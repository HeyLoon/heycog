from redbot.core import Config, commands, checks
import asyncio
import aiohttp
import discord
import time

class Bartender(commands.Cog):
    """點一些優質飲品()"""

    def __init__(self):
        self.config = Config.get_conf(self, identifier=822775204043948063)
        default_guild = {
            "bartenderDrinks": {
              "拿鐵": {
                "intro": "",
                "body": "",
                "images": [
                  "https://source.unsplash.com/kSlL887znkE/600x400"
                ],
                "emoji": "☕",
                "footer": "享受優質熱咖啡！",
              },
              "珍珠奶茶": {
                "intro": "非常好珍珠奶茶",
                "body": "",
                "images": [
                  "https://source.unsplash.com/P_wPicZYoPI/600x400"
                ],
                "emoji": "🧋",
                "footer": "跟你的朋友享受優質珍奶！",
              },
            }
        }

        self.config.register_guild(**default_guild)

    async def red_get_data_for_user(self, *, user_id: int):
        # this cog does not story any data
        return {}

    async def red_delete_data_for_user(self, *, requester, user_id: int) -> None:
        # this cog does not story any data
        pass


    # Utility Commands

    async def bartenderEmbed(self, ctx, drink, user):
        botcolor = await ctx.embed_colour()
        drinks = await self.config.guild(ctx.guild).bartenderDrinks()

        if drinks[drink]["intro"] != "":
            drinkintro = drinks[drink]["intro"]
        else:
            drinkintro = drink

        if drinks[drink]["body"] != "":
            drinkbody = "\n\n"+str(drinks[drink]["body"])
        else:
            drinkbody = ""

        drinkemoji = drinks[drink]["emoji"]
        desc = f"**{ctx.author.mention}** 給了 **{user}** 一杯 {drinkintro} {drinkemoji}{drinkbody}"
        e = discord.Embed(color=botcolor, description=desc)
        e.set_thumbnail(url=drinks[drink]["images"][0])
        e.set_footer(text=drinks[drink]["footer"])
        return e


    # Bot Commands

    @commands.command(aliases=["serve"])
    async def barserve(self, ctx, drink=None, *, user=None):
        """Serve a drink to a user"""
        drinks = await self.config.guild(ctx.guild).bartenderDrinks()
        if drink is not None and user is not None:
            try:
                e = await self.bartenderEmbed(ctx, drink, user)
                await ctx.send(embed=e)
            except KeyError:
                return await ctx.send(f"抱歉，我們沒有賣這種東西! 輸入 **{ctx.prefix}serve** 看看我們的菜單....")
        else:
            botcolor = await ctx.embed_colour()
            desc = ""
            for key in drinks:
              desc += str(drinks[key]["emoji"])+"\u2002"+str(key)+"\n"
            e = discord.Embed(color=botcolor, title="Menu 🪧", description=desc)
            e.set_footer(text=f"用 `{ctx.prefix}serve <drink> <@user>` 來點飲料")
            await ctx.send(embed=e)

    @commands.guild_only()
    @commands.group()
    @checks.admin_or_permissions(manage_guild=True)
    async def barset(self, ctx):
        """設定調酒師
        
        輸入 `[p]barserve` 查看菜單"""
        if not ctx.invoked_subcommand:
            pass

    @barset.command(name="add")
    async def barsetadd(self, ctx, name, emoji, imageUrl, intro=None):
        """加入飲料到菜單中"""
        drinks = await self.config.guild(ctx.guild).bartenderDrinks()
        if intro == None:
          intro = name
        try:
            drinks[name] = {
                "intro": intro,
                "body": "",
                "images": [
                  imageUrl
                ],
                "emoji": emoji,
                "footer": "",
            }
        except Exception as e:
            return await ctx.send("挖操....報錯了....\n"+str(e))
        await self.config.guild(ctx.guild).bartenderDrinks.set(drinks)
        await ctx.message.add_reaction("✅")

    @barset.command(name="remove")
    async def barsetremove(self, ctx, drinkname):
        """把飲料從菜單裡下架"""
        drinks = await self.config.guild(ctx.guild).bartenderDrinks()
        drinks.pop(drinkname, None)
        await self.config.guild(ctx.guild).bartenderDrinks.set(drinks)
        await ctx.message.add_reaction("✅")
