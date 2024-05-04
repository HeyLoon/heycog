import discord
import pytz
from datetime import datetime
from fuzzywuzzy import fuzz, process
from typing import Optional, Literal
from redbot.core import Config, commands
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import close_menu, menu, DEFAULT_CONTROLS

class Coffeetime(commands.Cog):
    """獲得世界各地的時間..."""
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, 278049241001, force_registration=True)
        default_user = {"usertime": None}
        self.config.register_user(**default_user)
        
    async def red_delete_data_for_user(
        self, *, requester: Literal["discord", "owner", "user", "user_strict"], user_id: int,
    ):
        await self.config.user_from_id(user_id).clear()

    async def get_usertime(self, user: discord.User):
        tz = None
        usertime = await self.config.user(user).usertime()
        if usertime:
            tz = pytz.timezone(usertime)

        return usertime, tz

    def fuzzy_timezone_search(self, tz: str):
        fuzzy_results = process.extract(tz.replace(" ", "_"), pytz.common_timezones, limit=500, scorer=fuzz.partial_ratio)
        matches = [x for x in fuzzy_results if x[1] > 98] 
        return matches

    async def format_results(self, ctx, tz):
        if not tz:
            await ctx.send(
                "抱歉，我們沒有找到你的國家的時區 :(\n試試這個列表裡的城市：\nhttps://coffeebank.github.io/timezone-picker"
            )
            return None
        elif len(tz) == 1:
            # command specific response, so don't do anything here
            return tz
        else:
            msg = ""
            for timezone in tz:
                msg += f"{timezone[0]}\n"

            embed_list = []
            for page in pagify(msg, delims=["\n"], page_length=500):
                e = discord.Embed(title=f"{len(tz)} 結果... 可以再精確一點嗎?\n\n 例如： `America/Los Angeles`", description=page)
                e.set_footer(text="https://coffeebank.github.io/timezone-picker")
                embed_list.append(e)
            if len(embed_list) == 1:
                close_control = {"\N{CROSS MARK}": close_menu}
                await menu(ctx, embed_list, close_control)
            else:
                await menu(ctx, embed_list, DEFAULT_CONTROLS)
            return None


    # Bot Commands

    @commands.command()
    async def time(self, ctx, user: discord.Member = None):
        """顯示目前的時間給特定使用者"""
        if not user:
            user = ctx.author
        usertime, tz = await self.get_usertime(user)
        if usertime:
            time = datetime.now(tz)
            fmt = "**%H:%M** *(%I:%M %p)*\n**%A, %d %B %Y**\n*%Z (UTC %z)*"
            time = time.strftime(fmt)

            timemsg1 = f"{user.display_name}那裡目前的時間是"
            timemsg2 = ""
            timemsg3 = f": \n>>> {str(time)}, *{usertime}*"
            timemsg4 = ""
            
            # Compare times
            if user != ctx.author:
                usertime, user_tz = await self.get_usertime(ctx.author)
                othertime, other_tz = await self.get_usertime(user)

                if usertime and othertime:
                    user_now = datetime.now(user_tz)
                    user_diff = user_now.utcoffset().total_seconds() / 60 / 60
                    other_now = datetime.now(other_tz)
                    other_diff = other_now.utcoffset().total_seconds() / 60 / 60
                    time_diff = abs(user_diff - other_diff)
                    time_diff_text = f"{time_diff:g}"
                    fmt = "**%H:%M %Z (UTC %z)**"
                    other_time = other_now.strftime(fmt)
                    plural = "" if time_diff_text == "1" else "s"
                    time_amt = "跟你那邊一樣" if time_diff_text == "0" else f"{time_diff_text} 時{plural}"
                    position = "比你早" if user_diff < other_diff else "比你晚"
                    position_text = "" if time_diff_text == "0" else f" {position}"

                    timemsg2 = f" **{time_amt}{position_text}**"
                else:
                  if not usertime:
                      timemsg4 = f"你還沒設定你的時區 👀 用 `{ctx.prefix}timeset` 來分享你的時間！"

            await ctx.send(timemsg1+timemsg2+timemsg3)
            if timemsg4:
              await ctx.send(timemsg4)
        else:
            await ctx.send(f"{user.display_name}還沒有設定時區。用 `{ctx.prefix}timeset` 來設定看看！")

    @commands.command()
    async def timeset(self, ctx, *, city_name_here):
        """
        設定你的時區

        最靠近你的大城市應該都可以....

        沒用？ [查一下你的時區 >](https://coffeebank.github.io/timezone-picker)
        """
        tz_results = self.fuzzy_timezone_search(city_name_here)
        tz_resp = await self.format_results(ctx, tz_results)
        if tz_resp:
            await self.config.user(ctx.author).usertime.set(tz_resp[0][0])
            await ctx.send(f"成功設定你的時區到 **{tz_resp[0][0]}**!")

    @commands.command()
    async def timein(self, ctx, *, city_name: str):
        """獲得這個時區的時間

        最靠近你的大城市應該都可以....

        沒用? [查一下你的時區 >](https://coffeebank.github.io/timezone-picker)
        """
        tz_results = self.fuzzy_timezone_search(city_name)
        tz_resp = await self.format_results(ctx, tz_results)
        if tz_resp:
            time = datetime.now(pytz.timezone(tz_resp[0][0]))
            fmt = "**%H:%M** *(%I:%M %p)*\n**%A, %d %B %Y**\n*%Z (UTC %z)"
            await ctx.send(">>> "+time.strftime(fmt)+f", {tz_resp[0][0]}*")

    @commands.guild_only()
    @commands.group()
    async def timetools(self, ctx):
        """
        確定時間
        在這裡找到你的時區和支援的時區列表:
        https://coffeebank.github.io/timezone-picker
        """
        pass

    @timetools.command()
    async def iso(self, ctx, *, iso_code=None):
        """尋找 ISO3166 國家代碼並為你提供支援的時區"""
        if iso_code is None:
            await ctx.send("這看起來不是正確的國家代碼！")
        else:
            exist = True if iso_code.upper() in pytz.country_timezones else False
            if exist is True:
                tz = str(pytz.country_timezones(iso_code.upper()))
                msg = (
                    f"支援的時區 **{iso_code.upper()}:**\n{tz[:-1][1:]}"
                    f"\n**使用** `{ctx.prefix}time tz Continent/City` **來顯示該時區目前的時間.**"
                )
                await ctx.send(msg)
            else:
                await ctx.send(
                    "這個代碼不受支援 \n完整的列表如下： "
                    "<https://en.wikipedia.org/wiki/List_of_ISO_3166_country_codes>\n"
                    "輸入兩個字母的代碼到 `Alpha-2 code` 欄."
                )

    @timetools.command()
    @commands.is_owner()
    async def set(self, ctx, user: discord.User, *, timezone_name=None):
        """
        允許機器人的擁有者編輯使用者的時區
        如果您的伺服器中不存在該使用者，請使用該使用者的使用者 ID。
        """
        if not user:
            user = ctx.author
        if len(self.bot.users) == 1:
            return await ctx.send("這個 cog 需要 Discord 的 Privileged Gateway Intents 才能正常運作")
        if user not in self.bot.users:
            return await ctx.send("我找不到這個人")
        if timezone_name is None:
            return await ctx.send_help()
        else:
            tz_results = self.fuzzy_timezone_search(timezone_name)
            tz_resp = await self.format_results(ctx, tz_results)
            if tz_resp:
                await self.config.user(user).usertime.set(tz_resp[0][0])
                await ctx.send(f"成功設定 {user.name} 的時區到 **{tz_resp[0][0]}**.")

    @timetools.command()
    async def user(self, ctx, user: discord.Member = None):
        """顯示特定的使用者目前的時間"""
        if not user:
            await ctx.send("這不是個使用者！")
        else:
            usertime, tz = await self.get_usertime(user)
            if usertime:
                time = datetime.now(tz)
                fmt = "**%H:%M** %d-%B-%Y **%Z (UTC %z)**"
                time = time.strftime(fmt)
                await ctx.send(
                    f"{user.name}目前的時區是: **{usertime}**\n" f"現在時間是： {str(time)}"
                )
            else:
                await ctx.send("這個使用者還沒有設定時區")

    @timetools.command()
    async def compare(self, ctx, user: discord.Member = None):
        """比較你跟其他使用者的時區"""
        if not user:
            return await ctx.send_help()

        usertime, user_tz = await self.get_usertime(ctx.author)
        othertime, other_tz = await self.get_usertime(user)

        if not usertime:
            return await ctx.send(
                f"你還沒設定時區，用 `{ctx.prefix}time me Continent/City` 來設定： "
                " <https://coffeebank.github.io/timezone-picker>"
            )
        if not othertime:
            return await ctx.send(f"這個使用者還沒設定時區")

        user_now = datetime.now(user_tz)
        user_diff = user_now.utcoffset().total_seconds() / 60 / 60
        other_now = datetime.now(other_tz)
        other_diff = other_now.utcoffset().total_seconds() / 60 / 60
        time_diff = abs(user_diff - other_diff)
        time_diff_text = f"{time_diff:g}"
        fmt = "**%H:%M %Z (UTC %z)**"
        other_time = other_now.strftime(fmt)
        plural = "" if time_diff_text == "1" else "s"
        time_amt = "跟你一樣" if time_diff_text == "0" else f"{time_diff_text} 時{plural}"
        position = "比你早" if user_diff < other_diff else "比你晚"
        position_text = "" if time_diff_text == "0" else f" {position}"

        await ctx.send(f"{user.display_name}的時間{other_time}{time_amt}{position_text}.")
