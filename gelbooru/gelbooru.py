import discord
import aiohttp
import re
import random
import logging
import urllib.parse
import html
from redbot.core import commands, app_commands, Config
from expiringdict import ExpiringDict

log = logging.getLogger("red.crab-cogs.boorucog")

EMBED_COLOR = 0xD7598B
EMBED_ICON = "https://i.imgur.com/FeRu6Pw.png"
IMAGE_TYPES = (".png", ".jpeg", ".jpg", ".webp", ".gif")
TAG_BLACKLIST = ["shota", "guro", "video"]
HEADERS = {
    "User-Agent": f"crab-cogs/v1 (https://github.com/hollowstrawberry/crab-cogs);"
}

class Booru(commands.Cog):
    """用斜線指令及 tag 在 Gelbooru 上搜尋圖片"""

    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.tag_cache = {}  # tag query -> tag results
        self.image_cache = ExpiringDict(max_len=100, max_age_seconds=24*60*60)  # channel id -> list of sent post ids
        self.config = Config.get_conf(self, identifier=62667275)
        self.config.register_global(tag_cache={})

    async def cog_load(self):
        self.tag_cache = await self.config.tag_cache()

    async def red_delete_data_for_user(self, requester: str, user_id: int):
        pass

    @commands.command()
    @commands.is_owner()
    async def boorudeletecache(self, ctx: commands.Context):
        self.tag_cache = {}
        async with self.config.tag_cache() as tag_cache:
            tag_cache.clear()
        await ctx.react_quietly("✅")

    @commands.hybrid_command(aliases=["gelbooru"])
    @app_commands.describe(tags="將自動建議標籤（請用空格分隔多個標籤）")
    async def booru(self, ctx: commands.Context, *, tags: str):
        """在 Gelbooru 搜尋圖片（請用空格分隔多個標籤）.
        
        在所有貼文都用完之前不會重複相同的貼文。
        在不是 NSFW 的頻道使用時將會開啟安全模式。
        輸入 - 來排除某些 tag 。
        你可以透過分數 :>NUMBER 來限制最低分數。
        也可以透過評價 rating:general / rating:sensitive / rating:questionable / rating:explicit 。"""

        tags = tags.strip()
        if tags.lower() in ["none", "error"]:
            tags = ""
        if not ctx.channel.nsfw:
            tags = re.sub(" ?rating:[^ ]+", "", tags)
            tags += " rating:general"

        try:
            result = await self.grab_image(tags, ctx)
        except:
            log.exception("無法從 Gelbooru 獲取圖片")
            await ctx.send("抱歉，在從 Gelbooru 獲取圖片時發生錯誤，請稍後再試或通知管理員。")
            return
        if not result:
            description = "💨 沒有結果..."
            if not ctx.channel.nsfw:
                description += " (safe mode)"
            await ctx.send(embed=discord.Embed(description=description, color=EMBED_COLOR))
            return

        embed = discord.Embed(color=EMBED_COLOR)
        embed.set_author(name="Booru 上的貼文", url=f"https://gelbooru.com/index.php?page=post&s=view&id={result['id']}", icon_url=EMBED_ICON)
        embed.set_image(url=result["file_url"] if result["width"]*result["height"] < 4200000 else result["sample_url"])
        if result.get("source", ""):
            embed.description = f"[🔗 貼文來源]({result['source']})"
        embed.set_footer(text=f"⭐ {result.get('score', 0)}")
        await ctx.send(embed=embed)

    @booru.autocomplete("tags")
    async def tags_autocomplete(self, interaction: discord.Interaction, current: str):
        if current is None:
            current = ""
        if ' ' in current:
            previous, last = [x.strip() for x in current.rsplit(' ', maxsplit=1)]
        else:
            previous, last = "", current.strip()
        excluded = last.startswith('-')
        last = last.lstrip('-')
        if not last and not excluded:
            # suggestions
            results = []
            if "full_body" not in previous:
                results.append("full_body")
            if "-" not in previous:
                results.append("-excluded_tag")
            if "score" not in previous:
                results += ["score:>10", "score:>100"]
            if interaction.channel.nsfw and "rating" not in previous:
                results += ["rating:general", "rating:sensitive", "rating:questionable", "rating:explicit"]
        elif "rating" in last.lower():
            if interaction.channel.nsfw:
                ratings = ["rating:general", "rating:sensitive", "rating:questionable", "rating:explicit"]
                results = []
                for r in tuple(ratings):
                    if r.startswith(last.lower()):
                        results.append(r)
                        ratings.remove(r)
                        break
                for r in ratings:
                    results.append(r)
            else:
                results = ["rating:general"]
                excluded = False
        elif "score" in last.lower():
            excluded = False
            results = ["score:>10", "score:>100", "score:>1000"]
            if re.match(r"score:>([0-9]+)", last):
                if last in results:
                    results.remove(last)
                results.insert(0, last)
        else:
            try:
                results = await self.grab_tags(last)
            except:
                log.exception("Failed to load Gelbooru tags")
                results = ["Error"]
                previous = None
        if excluded:
            results = [f"-{res}" for res in results]
        if previous:
            results = [f"{previous} {res}" for res in results]
        return [discord.app_commands.Choice(name=i, value=i) for i in results]

    async def grab_tags(self, query) -> list[str]:
        if query in self.tag_cache:
            return self.tag_cache[query].split(' ')
        query = urllib.parse.quote(query.lower(), safe=' ')
        url = f"https://gelbooru.com/index.php?page=dapi&s=tag&q=index&json=1&sort=desc&order_by=index_count&name_pattern=%25{query}%25"
        api = await self.bot.get_shared_api_tokens("gelbooru")
        api_key, user_id = api.get("api_key"), api.get("user_id")
        if api_key and user_id:
            url += f"&api_key={api_key}&user_id={user_id}"
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(url) as resp:
                data = await resp.json()
        if not data or "tag" not in data:
            return []
        results = [tag["name"] for tag in data["tag"]][:20]
        results = [html.unescape(tag) for tag in results]
        self.tag_cache[query] = ' '.join(results)
        async with self.config.tag_cache() as tag_cache:
            tag_cache[query] = self.tag_cache[query]
        return results

    async def grab_image(self, query: str, ctx: commands.Context) -> dict:
        query = urllib.parse.quote(query.lower(), safe=' ')
        tags = [tag for tag in query.split(' ') if tag]
        tags = [tag for tag in tags if tag not in TAG_BLACKLIST]
        tags += [f"-{tag}" for tag in TAG_BLACKLIST]
        query = ' '.join(tags)
        url = "https://gelbooru.com/index.php?page=dapi&s=post&q=index&json=1&limit=1000&tags=" + query.replace(' ', '+')
        api = await self.bot.get_shared_api_tokens("gelbooru")
        api_key, user_id = api.get("api_key"), api.get("user_id")
        if api_key and user_id:
            url += f"&api_key={api_key}&user_id={user_id}"
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(url) as resp:
                data = await resp.json()
        if not data or "post" not in data:
            return {}
        images = [img for img in data["post"] if img["file_url"].endswith(IMAGE_TYPES)]
        # prevent duplicates
        key = ctx.channel.id
        if key not in self.image_cache:
            self.image_cache[key] = []
        if all(img["id"] in self.image_cache[key] for img in images):
            self.image_cache[key] = self.image_cache[key][-1:]
        if len(images) > 1:
            images = [img for img in images if img["id"] not in self.image_cache[key]]
        choice = random.choice(images)
        self.image_cache[key].append(choice["id"])
        return choice
