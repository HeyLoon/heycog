import base64
import re
from asyncio import TimeoutError as AsyncTimeoutError
from io import BytesIO
from typing import Optional

import aiohttp
import discord
from mcstatus import BedrockServer, JavaServer
from redbot.core import commands
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils import chat_formatting as chat

from .minecraftplayer import MCPlayer

try:
    from redbot import json  # support of Draper's branch
except ImportError:
    import json


_ = Translator("MinecraftData", __file__)


@cog_i18n(_)
class MinecraftData(commands.Cog):
    """Minecraft 的相關資料"""

    __version__ = "2.2.2+code_opt"

    # noinspection PyMissingConstructor
    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession(json_serialize=json.dumps)

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    def format_help_for_context(self, ctx: commands.Context) -> str:  # Thanks Sinbad!
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\n\n**版本**: {self.__version__}"

    async def red_delete_data_for_user(self, **kwargs):
        return

    @commands.group(aliases=["mc"])
    async def minecraft(self, ctx):
        """取得與 Minecraft 相關的資料"""
        pass

    @minecraft.command(usage="<player> [overlay layer=True]")
    @commands.bot_has_permissions(embed_links=True)
    async def skin(self, ctx, player: MCPlayer, overlay: bool = True):
        """透過玩家名稱取得 Minecraft Java 版的皮膚"""
        uuid = player.uuid
        stripname = player.name.strip("_")
        files = []
        async with ctx.channel.typing():
            try:
                async with self.session.get(
                    f"https://crafatar.com/renders/head/{uuid}",
                    params="overlay" if overlay else None,
                ) as s:
                    files.append(
                        discord.File(
                            head_file := BytesIO(await s.read()), filename=f"{stripname}_head.png"
                        )
                    )
                async with self.session.get(f"https://crafatar.com/skins/{uuid}") as s:
                    files.append(
                        discord.File(
                            skin_file := BytesIO(await s.read()), filename=f"{stripname}.png"
                        )
                    )
                async with self.session.get(
                    f"https://crafatar.com/renders/body/{uuid}.png",
                    params="overlay" if overlay else None,
                ) as s:
                    files.append(
                        discord.File(
                            body_file := BytesIO(await s.read()), filename=f"{stripname}_body.png"
                        )
                    )
            except aiohttp.ClientResponseError as e:
                await ctx.send(
                    chat.error(_("無法從 Crafatar 獲取資料: {}").format(e.message))
                )
                return
        em = discord.Embed(timestamp=ctx.message.created_at, color=await ctx.embed_color())
        em.set_author(
            name=player.name,
            icon_url=f"attachment://{stripname}_head.png",
            url=f"https://crafatar.com/skins/{uuid}",
        )
        em.set_thumbnail(url=f"attachment://{stripname}.png")
        em.set_image(url=f"attachment://{stripname}_body.png")
        em.set_footer(text=_("由 Crafatar 提供"), icon_url="https://crafatar.com/logo.png")
        await ctx.send(embed=em, files=files)
        head_file.close()
        skin_file.close()
        body_file.close()

    @minecraft.group(invoke_without_command=True)
    @commands.bot_has_permissions(embed_links=True)
    async def cape(self, ctx, player: MCPlayer):
        """透過玩家名稱取得玩家的 Minecraft 披風"""
        try:
            await self.session.get(
                f"https://crafatar.com/capes/{player.uuid}", raise_for_status=True
            )
        except aiohttp.ClientResponseError as e:
            if e.status == 404:
                await ctx.send(chat.error(_("{} 沒有披風").format(player.name)))
            else:
                await ctx.send(chat.error(_("無法獲取披風: {}").format(e.message)))
            return
        em = discord.Embed(timestamp=ctx.message.created_at, color=await ctx.embed_color())
        em.set_author(name=player.name, url=f"https://crafatar.com/capes/{player.uuid}")
        em.set_image(url=f"https://crafatar.com/capes/{player.uuid}")
        await ctx.send(embed=em)

    @cape.command(aliases=["of"])
    async def optifine(self, ctx, player: MCPlayer):
        """透過玩家名稱取得玩家的 Optifine 披風"""
        try:
            await self.session.get(
                f"http://s.optifine.net/capes/{player.name}.png", raise_for_status=True
            )
        except aiohttp.ClientResponseError as e:
            if e.status == 404:
                await ctx.send(chat.error(_("{} 沒有 OptiFine 披風").format(player.name)))
            else:
                await ctx.send(
                    chat.error(
                        _("無法取得 {player} 的 OptiFine 披風: {message}").format(
                            player=player.name, message=e.message
                        )
                    )
                )
            return
        em = discord.Embed(timestamp=ctx.message.created_at, color=await ctx.embed_color())
        em.set_author(name=player.name, url=f"http://s.optifine.net/capes/{player.name}.png")
        em.set_image(url=f"http://s.optifine.net/capes/{player.name}.png")
        await ctx.send(embed=em)

    @cape.command()
    async def labymod(self, ctx, player: MCPlayer):
        """透過玩家名稱取得玩家的 LabyMod 披風"""
        uuid = player.dashed_uuid
        try:
            async with self.session.get(
                f"http://capes.labymod.net/capes/{uuid}", raise_for_status=True
            ) as data:
                cape = await data.read()
        except aiohttp.ClientResponseError as e:
            if e.status == 404:
                await ctx.send(chat.error(_("{} 沒有 LabyMod 披風").format(player.name)))
            else:
                await ctx.send(
                    chat.error(
                        _("無法取得資料: {message} ({status})").format(
                            status=e.status, message=e.message
                        )
                    )
                )
            return
        cape = BytesIO(cape)
        file = discord.File(cape, filename="{}.png".format(player))
        await ctx.send(file=file)
        cape.close()

    @cape.command(aliases=["minecraftcapes", "couk"])
    async def mccapes(self, ctx, player: MCPlayer):
        """透過玩家名稱取得玩家的 MinecraftCapes.co.uk 的披風"""
        try:
            await self.session.get(
                f"https://minecraftcapes.co.uk/getCape/{player.uuid}",
                raise_for_status=True,
            )
        except aiohttp.ClientResponseError as e:
            if e.status == 404:
                await ctx.send(
                    chat.error(_("{} 沒有MinecraftCapes.co.uk的披風").format(player.name))
                )
            else:
                await ctx.send(
                    chat.error(
                        _("無法取得 {player} 的 MinecraftCapes.co.uk 披風: {message}").format(
                            player=player.name, message=e.message
                        )
                    )
                )
            return
        em = discord.Embed(timestamp=ctx.message.created_at, color=await ctx.embed_color())
        em.set_author(
            name=player.name, url=f"https://minecraftcapes.net/profile/{player.uuid}/cape"
        )
        em.set_image(url=f"https://minecraftcapes.net/profile/{player.uuid}/cape")
        await ctx.send(embed=em)

    @cape.group(aliases=["5zig"], invoke_without_command=True)
    async def fivezig(self, ctx, player: MCPlayer):
        """透過玩家名稱取得玩家的 5zig 披風"""
        uuid = player.uuid
        try:
            async with self.session.get(
                f"http://textures.5zig.net/textures/2/{uuid}", raise_for_status=True
            ) as data:
                response_data = await data.json(content_type=None, loads=json.loads)
            cape = response_data["cape"]
        except aiohttp.ClientResponseError as e:
            if e.status == 404:
                await ctx.send(chat.error(_("{} 沒有 5zig 的披風").format(player.name)))
            else:
                await ctx.send(
                    chat.error(
                        _("無法取得 {player} 的 5zig 披風: {message}").format(
                            player=player.name, message=e.message
                        )
                    )
                )
            return
        cape = BytesIO(base64.decodebytes(cape.encode()))
        file = discord.File(cape, filename="{}.png".format(player))
        await ctx.send(file=file)
        cape.close()

    @fivezig.command(name="animated")
    async def fivezig_animated(self, ctx, player: MCPlayer):
        """透過玩家名稱取得玩家的 5zig 動態披風"""
        uuid = player.uuid
        try:
            async with self.session.get(
                f"http://textures.5zig.net/textures/2/{uuid}", raise_for_status=True
            ) as data:
                response_data = await data.json(content_type=None, loads=json.loads)
            if "animatedCape" not in response_data:
                await ctx.send(
                    chat.error(_("{} 沒有 5zig 的動態披風")).format(player.name)
                )
                return
            cape = response_data["animatedCape"]
        except aiohttp.ClientResponseError as e:
            if e.status == 404:
                await ctx.send(chat.error(_("{} 沒有 5zig 的披風").format(player.name)))
            else:
                await ctx.send(
                    chat.error(
                        _("無法取得 {player} 的 5zig 披風: {message}").format(
                            player=player.name, message=e.message
                        )
                    )
                )
            return
        cape = BytesIO(base64.decodebytes(cape.encode()))
        file = discord.File(cape, filename="{}.png".format(player))
        await ctx.send(file=file)
        cape.close()

    @minecraft.group()
    @commands.bot_has_permissions(embed_links=True)
    async def server(self, ctx):
        """獲取 Minecraft 伺服器的資訊"""
        pass

    @server.command(usage="[query=False] <server IP>[:port]")
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def java(self, ctx, query_data: Optional[bool], server_ip: str):
        """獲取 Minecraft Java 版伺服器的資訊"""
        try:
            server: JavaServer = await self.bot.loop.run_in_executor(
                None, JavaServer.lookup, server_ip
            )
        except Exception as e:
            await ctx.send(chat.error(_("無法解析 IP: {}").format(e)))
            return
        async with ctx.channel.typing():
            try:
                status = await server.async_status()
            except OSError as e:
                await ctx.send(chat.error(_("無法獲取伺服器狀態: {}").format(e)))
                return
            except AsyncTimeoutError:
                await ctx.send(chat.error(_("無法獲取伺服器狀態: 連線逾時")))
                return
        icon_file = None
        icon = (
            discord.File(
                icon_file := BytesIO(base64.b64decode(status.favicon.split(",", 1)[1])),
                filename="icon.png",
            )
            if status.favicon
            else None
        )
        embed = discord.Embed(
            title=f"{server.address.host}:{server.address.port}",
            description=chat.box(await self.clear_mcformatting(status.description)),
            color=await ctx.embed_color(),
        )
        if icon:
            embed.set_thumbnail(url="attachment://icon.png")
        embed.add_field(name=_("延遲"), value=f"{status.latency:.2f} ms")
        embed.add_field(
            name=_("玩家人數"),
            value="{0.players.online}/{0.players.max}\n{1}".format(
                status,
                (
                    chat.box(
                        list(
                            chat.pagify(
                                await self.clear_mcformatting(
                                    "\n".join([p.name for p in status.players.sample])
                                ),
                                page_length=992,
                            )
                        )[0]
                    )
                    if status.players.sample
                    else ""
                ),
            ),
        )
        embed.add_field(
            name=_("版本"),
            value=("{}" + "\n" + _("協議: {}")).format(
                status.version.name, status.version.protocol
            ),
        )
        msg = await ctx.send(file=icon, embed=embed)
        if icon_file:
            icon_file.close()
        if query_data:
            try:
                query = await server.async_query()
            except OSError as e:
                embed.set_footer(text=chat.error(_("無法獲取查詢數據: {}").format(e)))
                await msg.edit(embed=embed)
                return
            except AsyncTimeoutError:
                embed.set_footer(text=chat.error(_("無法獲取查詢數據: 連線逾時")))
                await msg.edit(embed=embed)
                return
            embed.add_field(name=_("世界"), value=f"{query.map}")
            embed.add_field(
                name=_("軟體"),
                value=f"{query.software.brand}"
                + "\n"
                + _("版本: {}").format(query.software.version)
                + "\n"
                + _("插件: {}").format(", ".join(query.software.plugins)),
            )
            await msg.edit(embed=embed)

    @server.command(usage="<server IP>[:port]")
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def bedrock(self, ctx, server_ip: str):
        """獲取 Minecraft Bedrock 版伺服器的資訊"""
        try:
            server: BedrockServer = await self.bot.loop.run_in_executor(
                None, BedrockServer.lookup, server_ip
            )
        except Exception as e:
            await ctx.send(chat.error(_("無法解析 IP: {}").format(e)))
            return
        async with ctx.channel.typing():
            try:
                status = await server.async_status()
            except OSError as e:
                await ctx.send(chat.error(_("無法獲取伺服器狀態: {}").format(e)))
                return
            except AsyncTimeoutError:
                await ctx.send(chat.error(_("無法獲取伺服器狀態: 連線逾時")))
                return
        embed = discord.Embed(
            title=f"{server.address.host}:{server.address.port}",
            description=chat.box(await self.clear_mcformatting(status.motd)),
            color=await ctx.embed_color(),
        )
        embed.add_field(name=_("延遲"), value=f"{status.latency:.2f} ms")
        embed.add_field(name=_("玩家人數"), value=f"{status.players_online}/{status.players_max}"),
        embed.add_field(
            name=_("版本"),
            value=("{}" + "\n" + _("協議: {}") + "\n" + _("品牌: {}")).format(
                status.version.version, status.version.protocol, status.version.brand
            ),
        )
        embed.add_field(name=_("地圖"), value=status.map)
        embed.add_field(name=_("遊戲模式"), value=status.gamemode)
        await ctx.send(embed=embed)

    # @minecraft.command(aliases=["nicknames", "nickhistory", "names"])
    # async def nicks(self, ctx, current_nick: MCPlayer):
    #     """Check history of player's nicks"""
    #     uuid = current_nick.uuid
    #     try:
    #         async with self.session.get(
    #             "https://api.mojang.com/user/profiles/{}/names".format(uuid)
    #         ) as data:
    #             data_history = await data.json(loads=json.loads)
    #         for nick in data_history:
    #             try:
    #                 nick["changedToAt"] = format_datetime(
    #                     datetime.fromtimestamp(nick["changedToAt"] / 1000, timezone.utc),
    #                     locale=get_babel_regional_format(),
    #                 )
    #             except KeyError:
    #                 nick["changedToAt"] = _("Initial")
    #         table = tabulate.tabulate(
    #             data_history,
    #             headers={
    #                 "name": _("Nickname"),
    #                 "changedToAt": _("Changed to at... (UTC)"),
    #             },
    #             tablefmt="orgtbl",
    #         )
    #         pages = [chat.box(page) for page in list(chat.pagify(table))]
    #         await menu(ctx, pages, DEFAULT_CONTROLS)
    #     except Exception as e:
    #         await ctx.send(
    #             chat.error(
    #                 _("Unable to check name history.\nAn error has been occurred: ")
    #                 + chat.inline(str(e))
    #             )
    #         )

    async def clear_mcformatting(self, formatted_str) -> str:
        """移除 Minecraft 格式"""
        if not isinstance(formatted_str, dict):
            return re.sub(r"\xA7[0-9A-FK-OR]", "", formatted_str, flags=re.IGNORECASE)
        clean = ""
        async for text in self.gen_dict_extract("text", formatted_str):
            clean += text
        return re.sub(r"\xA7[0-9A-FK-OR]", "", clean, flags=re.IGNORECASE)

    async def gen_dict_extract(self, key: str, var: dict):
        if not hasattr(var, "items"):
            return
        for k, v in var.items():
            if k == key:
                yield v
            if isinstance(v, dict):
                async for result in self.gen_dict_extract(key, v):
                    yield result
            elif isinstance(v, list):
                for d in v:
                    async for result in self.gen_dict_extract(key, d):
                        yield result
