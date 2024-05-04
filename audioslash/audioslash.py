from youtubesearchpython.__future__ import VideosSearch
import logging
import discord
from copy import copy
from redbot.core import commands, app_commands
from redbot.core.bot import Red
from redbot.core.commands import Cog
from redbot.cogs.audio import Audio
from redbot.cogs.audio.utils import PlaylistScope
from redbot.cogs.audio.converters import PlaylistConverter, ScopeParser
from redbot.cogs.audio.apis.playlist_interface import get_all_playlist
from typing import Optional

log = logging.getLogger("red.crab-cogs.audioslash")


class AudioSlash(Cog):
    """支援 YouTube 和播放清單功能的斜線指令版音樂播放 cog 。"""

    def __init__(self, bot: Red, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot

    async def red_delete_data_for_user(self, **kwargs):
        pass

    async def get_audio_cog(self, inter: discord.Interaction) -> Optional[Audio]:
        cog: Optional[Audio] = self.bot.get_cog("Audio")
        if cog:
            return cog
        await inter.response.send_message("Audio cog 沒有載入！", ephemeral=True)

    async def get_context(self, inter: discord.Interaction, cog: Audio) -> commands.Context:
        ctx: commands.Context = await self.bot.get_context(inter)  # noqa
        ctx.command.cog = cog
        return ctx

    async def can_run_command(self, ctx: commands.Context, command_name: str) -> bool:
        prefix = await self.bot.get_prefix(ctx.message)
        prefix = prefix[0] if isinstance(prefix, list) else prefix
        fake_message = copy(ctx.message)
        fake_message.content = prefix + command_name
        command = ctx.bot.get_command(command_name)
        fake_context: commands.Context = await ctx.bot.get_context(fake_message)  # noqa
        try:
            can = await command.can_run(fake_context, check_all_parents=True, change_permission_state=False)
        except commands.CommandError:
            can = False
        if not can:
            await ctx.send("你沒有權限", ephemeral=True)
        return can

    @app_commands.command()
    @app_commands.guild_only
    @app_commands.describe(search="在此輸入以獲得最相似的結果",
                           when="你可以決定該曲目何時可以在序列中播放")
    @app_commands.choices(when=[app_commands.Choice(name="加到序列的最後", value="end"),
                                app_commands.Choice(name="這首播完後播放", value="next"),
                                app_commands.Choice(name="切歌", value="now")])
    async def play(self, inter: discord.Interaction, search: str, when: Optional[str]):
        """在語音頻道裡播放 YouTube 的曲目"""
        if not (audio := await self.get_audio_cog(inter)):
            return
        ctx = await self.get_context(inter, audio)
        if when in ("next", "now"):
            if not await self.can_run_command(ctx, "bumpplay"):
                return
            await audio.command_bumpplay(ctx, when == "now", query=search)
        else:
            if not await self.can_run_command(ctx, "play"):
                return
            await audio.command_play(ctx, query=search)

    @app_commands.command()
    @app_commands.guild_only
    async def pause(self, inter: discord.Interaction):
        """暫停或續播語音頻道裡的曲目"""
        if not (audio := await self.get_audio_cog(inter)):
            return
        ctx = await self.get_context(inter, audio)
        if not await self.can_run_command(ctx, "pause"):
            return
        await audio.command_pause(ctx)

    @app_commands.command()
    @app_commands.guild_only
    async def stop(self, inter: discord.Interaction):
        """切掉語音頻道裡的曲目"""
        if not (audio := await self.get_audio_cog(inter)):
            return
        ctx = await self.get_context(inter, audio)
        if not await self.can_run_command(ctx, "stop"):
            return
        await audio.command_stop(ctx)

    @app_commands.command()
    @app_commands.guild_only
    @app_commands.describe(position="跳過這首曲目")
    async def skip(self, inter: discord.Interaction, position: Optional[app_commands.Range[int, 1, 1000]]):
        """跳過序列中的一些曲目"""
        if not (audio := await self.get_audio_cog(inter)):
            return
        ctx = await self.get_context(inter, audio)
        if not await self.can_run_command(ctx, "skip"):
            return
        await audio.command_skip(ctx, position)

    @app_commands.command()
    @app_commands.guild_only
    async def queue(self, inter: discord.Interaction):
        """看看現在在播什麼"""
        if not (audio := await self.get_audio_cog(inter)):
            return
        ctx = await self.get_context(inter, audio)
        if not await self.can_run_command(ctx, "queue"):
            return
        await audio.command_queue(ctx)

    toggle = [app_commands.Choice(name="啟用", value="1"),
              app_commands.Choice(name="關閉", value="0")]

    @app_commands.command()
    @app_commands.guild_only
    @app_commands.describe(volume="設定音量(1~150)")
    async def volume(self, inter: discord.Interaction, volume: app_commands.Range[int, 1, 150]):
        """設定音樂的音量"""
        if not (audio := await self.get_audio_cog(inter)):
            return
        ctx = await self.get_context(inter, audio)
        if not await self.can_run_command(ctx, "volume"):
            return
        await audio.command_volume(ctx, volume)

    @app_commands.command()
    @app_commands.guild_only
    @app_commands.describe(toggle="開啟或關閉隨機播放")
    @app_commands.choices(toggle=toggle)
    async def shuffle(self, inter: discord.Interaction, toggle: str):
        """設定播放清單要不要隨機播放"""
        if not (audio := await self.get_audio_cog(inter)):
            return
        ctx = await self.get_context(inter, audio)
        value = bool(int(toggle))
        if value != await audio.config.guild(ctx.guild).shuffle():
            if not await self.can_run_command(ctx, "shuffle"):
                return
            await audio.command_shuffle(ctx)
        else:
            embed = discord.Embed(title="設定沒有變更", description="隨機播放: " + ("Enabled" if value else "Disabled"))
            await audio.send_embed_msg(ctx, embed=embed)

    @app_commands.command()
    @app_commands.guild_only
    @app_commands.describe(toggle="開啟或關閉無限輪播")
    @app_commands.choices(toggle=toggle)
    async def repeat(self, inter: discord.Interaction, toggle: str):
        """設定播放清單要不要無限重播"""
        if not (audio := await self.get_audio_cog(inter)):
            return
        ctx = await self.get_context(inter, audio)
        value = bool(int(toggle))
        if value != await audio.config.guild(ctx.guild).repeat():
            if not await self.can_run_command(ctx, "repeat"):
                return
            await audio.command_repeat(ctx)
        else:
            embed = discord.Embed(title="設定沒有變更", description="無限重播: " + ("Enabled" if value else "Disabled"))
            await audio.send_embed_msg(ctx, embed=embed)

    playlist = app_commands.Group(name="playlist", description="播放清單指令", guild_only=True)

    playlist_scopes = [app_commands.Choice(name="個人", value="USERPLAYLIST"),
                       app_commands.Choice(name="伺服器", value="GUILDPLAYLIST"),
                       app_commands.Choice(name="公開", value="GLOBALPLAYLIST")]

    @staticmethod
    def get_scope_data(scope: str, ctx: commands.Context) -> ScopeParser:
        return [scope, ctx.author, ctx.guild, False]  # noqa

    @playlist.command(name="play")
    @app_commands.describe(playlist="播放清單名稱",
                           shuffle="是否開啟隨機播放")
    async def playlist_play(self, inter: discord.Interaction, playlist: str, shuffle: Optional[bool]):
        """開始播放已存在的播放清單"""
        if not (audio := await self.get_audio_cog(inter)):
            return
        ctx = await self.get_context(inter, audio)
        match = await PlaylistConverter().convert(ctx, playlist)
        enabled = False
        if shuffle is not None and shuffle != await audio.config.guild(ctx.guild).shuffle():
            dj_enabled = audio._dj_status_cache.setdefault(ctx.guild.id, await audio.config.guild(ctx.guild).dj_enabled())
            can_skip = await audio._can_instaskip(ctx, ctx.author)
            if not dj_enabled or can_skip and await self.can_run_command(ctx, "shuffle"):
                await audio.config.guild(ctx.guild).shuffle.set(shuffle)
                enabled = shuffle
        if not await self.can_run_command(ctx, "playlist play"):
            return
        await audio.command_playlist_start(ctx, match)
        if enabled:
            await audio.config.guild(ctx.guild).shuffle.set(False)

    @playlist.command(name="create")
    @app_commands.describe(name="播放清單的名稱(不能有空白鍵)",
                           make_from_queue="將目前序列中的歌曲填入播放清單",
                           scope="設定播放清單所有權")
    @app_commands.choices(scope=playlist_scopes)
    async def playlist_create(self, inter: discord.Interaction, name: str, make_from_queue: Optional[bool], scope: Optional[str]):
        """創建新的播放清單"""
        if not (audio := await self.get_audio_cog(inter)):
            return
        name = name.replace(" ", "-")
        ctx = await self.get_context(inter, audio)
        if make_from_queue:
            if not await self.can_run_command(ctx, "playlist queue"):
                return
            await audio.command_playlist_queue(ctx, name, scope_data=self.get_scope_data(scope, ctx))
        else:
            if not await self.can_run_command(ctx, "playlist create"):
                return
            await audio.command_playlist_create(ctx, name, scope_data=self.get_scope_data(scope, ctx))

    @playlist.command(name="add")
    @app_commands.describe(playlist="播放清單名稱",
                           track="要加入播放清單的曲目",
                           scope="設定播放清單所有權")
    @app_commands.choices(scope=playlist_scopes)
    async def playlist_add(self, inter: discord.Interaction, playlist: str, track: str, scope: Optional[str]):
        """加入新的曲目進到播放清單"""
        if not (audio := await self.get_audio_cog(inter)):
            return
        ctx = await self.get_context(inter, audio)
        match = await PlaylistConverter().convert(ctx, playlist)
        if not await self.can_run_command(ctx, "playlist append"):
            return
        await audio.command_playlist_append(ctx, match, track, scope_data=self.get_scope_data(scope, ctx))

    @playlist.command(name="remove")
    @app_commands.describe(playlist="播放清單名稱",
                           track="要從播放清單刪除的曲目",
                           scope="設定播放清單所有權")
    @app_commands.choices(scope=playlist_scopes)
    async def playlist_remove(self, inter: discord.Interaction, playlist: str, track: str, scope: Optional[str]):
        """從播放清單中刪除歌曲"""
        if not (audio := await self.get_audio_cog(inter)):
            return
        ctx = await self.get_context(inter, audio)
        match = await PlaylistConverter().convert(ctx, playlist)
        if not await self.can_run_command(ctx, "playlist remove"):
            return
        await audio.command_playlist_remove(ctx, match, track, scope_data=self.get_scope_data(scope, ctx))

    @playlist.command(name="info")
    @app_commands.describe(playlist="播放清單名稱",
                           scope="設定播放清單所有權")
    @app_commands.choices(scope=playlist_scopes)
    async def playlist_info(self, inter: discord.Interaction, playlist: str, scope: Optional[str]):
        """顯示播放清單的詳細資訊"""
        if not (audio := await self.get_audio_cog(inter)):
            return
        ctx = await self.get_context(inter, audio)
        match = await PlaylistConverter().convert(ctx, playlist)
        if not await self.can_run_command(ctx, "playlist info"):
            return
        await audio.command_playlist_info(ctx, match, scope_data=self.get_scope_data(scope, ctx))

    @playlist.command(name="delete")
    @app_commands.describe(playlist="播放清單名稱",
                           scope="設定播放清單所有權")
    @app_commands.choices(scope=playlist_scopes)
    async def playlist_delete(self, inter: discord.Interaction, playlist: str, scope: Optional[str]):
        """刪除整個播放清單"""
        if not (audio := await self.get_audio_cog(inter)):
            return
        ctx = await self.get_context(inter, audio)
        match = await PlaylistConverter().convert(ctx, playlist)
        if not await self.can_run_command(ctx, "playlist delete"):
            return
        await audio.command_playlist_delete(ctx, match, scope_data=self.get_scope_data(scope, ctx))

    @staticmethod
    def format_youtube(res: dict) -> str:
        name = f"({res['duration']}) {res['title']}"
        author = f" — {res['channel']['name']}"
        if len(name) + len(author) > 100:
            return name[:97 - len(author)] + "..." + author
        else:
            return name + author

    @play.autocomplete("search")
    @playlist_add.autocomplete("track")
    async def youtube_autocomplete(self, _: discord.Interaction, current: str):
        try:
            if not current:
                return []
            search = VideosSearch(current, limit=20)
            results = await search.next()
            return [app_commands.Choice(name=self.format_youtube(res), value=res["link"]) for res in results["result"]]
        except:
            log.exception("搜尋結果")

    @playlist_play.autocomplete("playlist")
    @playlist_add.autocomplete("playlist")
    @playlist_remove.autocomplete("playlist")
    @playlist_info.autocomplete("playlist")
    @playlist_delete.autocomplete("playlist")
    async def playlist_autocomplete(self, inter: discord.Interaction, current: str):
        audio: Optional[Audio] = self.bot.get_cog("Audio")
        if not audio or not audio.playlist_api:
            return []
        try:
            global_matches = await get_all_playlist(
                PlaylistScope.GLOBAL.value, self.bot, audio.playlist_api, inter.guild, inter.user
            )
            guild_matches = await get_all_playlist(
                PlaylistScope.GUILD.value, self.bot, audio.playlist_api, inter.guild, inter.user
            )
            user_matches = await get_all_playlist(
                PlaylistScope.USER.value, self.bot, audio.playlist_api, inter.guild, inter.user
            )
            playlists = [*user_matches, *guild_matches, *global_matches]
            if current:
                results = [pl.name for pl in playlists if pl.name.lower().startswith(current.lower())]
                results += [pl.name for pl in playlists if current.lower() in pl.name.lower() and not pl.name.lower().startswith(current.lower())]
            else:
                results = [pl.name for pl in playlists]
            return [app_commands.Choice(name=pl, value=pl) for pl in results][:25]
        except:
            log.exception("Retrieving playlists")
