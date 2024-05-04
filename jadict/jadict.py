from redbot.core import Config, app_commands, commands, checks
from redbot.core.utils.views import SimpleMenu
import urllib.parse
import discord
import asyncio
import aiohttp
import json

from .jadict_utils import *

class Jadict(commands.Cog):
    """日語辭典機器人，使用 Jisho API 在 Jisho 上搜索"""

    def __init__(self, bot):
        self.config = Config.get_conf(self, identifier=806715409318936616)
        self.bot = bot

    # This cog does not store any End User Data
    async def red_get_data_for_user(self, *, user_id: int):
        return {}
    async def red_delete_data_for_user(self, *, requester, user_id: int) -> None:
        pass


    # Utility Commands

    async def jishoResultsEmbeds(self, ctx, jishoResult):
        sendEmbeds = []
        total = len(jishoResult or [])
        for idx, jisho_results in enumerate(jishoResult):
            e = discord.Embed(
              color=(await self.bot.get_embed_colour(self)),
              title=jisho_results["title"],
              url=jisho_results["url"],
              description=jisho_results["description"]
            )
            for sense in jisho_results["senses"]:
                e.add_field(
                    name=sense["name"], 
                    value=sense["value"],
                    inline=True
                )
            e.set_footer(text=" ・ ".join(filter(None, [jisho_results["attribution"], str(idx+1)+"/"+str(total)])))
            sendEmbeds.append({"embed": e})
        return sendEmbeds

    async def fallbackEmbed(self, ctx, rawText, footer=""):
        text = urllib.parse.quote(rawText, safe='')
        e = discord.Embed(color=(await self.bot.get_embed_colour(self)), title=rawText)
        e.add_field(name="Jisho", value=f"https://jisho.org/search/{text}")
        e.add_field(name="Wiktionary", value=f"https://zh.wiktionary.org/w/index.php?fulltext=0&search={text}")
        e.add_field(name="DeepL Translate", value=f"https://deepl.com/translator#ja/zh/{text}")
        e.add_field(name="Google Translate", value=f"https://translate.google.com/?text={text}")

        if footer:
            e.set_footer(text=footer)
        return e
  


    # Bot Commands

    @commands.hybrid_command(name="jadict", aliases=["jpdict", "jisho", "jishosearch"])
    @app_commands.describe(text="搜尋日語辭典。預設情況下用羅馬拼音及日語輸入，在英語情況下請使用  \"quotes\"")
    async def jadict(self, ctx, *, text):
        """搜尋日語辭典

        素材來自 [Jisho](https://jisho.org) 、 JMdict 、 JMnedict 、 DBpedia 和 Wikipedia.
        
        預設情況下用羅馬拼音及日語輸入，在英語情況下請使用  **`"quotes"`** .
        > ✅  東京, toukyou, or "tokyo"
        > ✅  らーめん, raamen, or "ramen"
        """
        jishoJson = await fetchJisho(text)

        if jishoJson not in [False, None]:
            jisho_results = make_results(jishoJson)
            sendEmbeds = await self.jishoResultsEmbeds(ctx, jisho_results)
            await SimpleMenu(pages=sendEmbeds, timeout=90).start(ctx)
        elif jishoJson is False:
            fallback_embed = await self.fallbackEmbed(ctx, text, "在 Jisho 上沒有找到內容，請嘗試其他來源")
            return await ctx.send(embed=fallback_embed)
        else:
            fallback_embed = await self.fallbackEmbed(ctx, text, "無法連接到 Jisho API")
            return await ctx.send(embed=fallback_embed)

    @commands.hybrid_command(name="jasearch", aliases=["jpsearch"])
    @app_commands.describe(text="搜尋日語單字或翻譯網站")
    async def jasearch(self, ctx, *, text):
        """搜尋日語單字或翻譯網站"""
        fallback_embed = await self.fallbackEmbed(ctx, text)
        return await ctx.send(embed=fallback_embed)
