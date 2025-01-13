import discord
from discord.ext import commands
import random
import asyncio
from discord.ui import Button, View

# معلومات البوت
BOT_NAME = "🎲 Lucky Numbers"
BOT_OWNER = "! 𝕆𝕄𝔸ℝ"
BOT_VERSION = "1.0.0"

# إعداد البوت مع جميع الصلاحيات المطلوبة
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

class NumberGame:
    def __init__(self):
        self.reset()

    def reset(self):
        self.is_active = False
        self.players = set()
        self.active_players = set()
        self.current_round = 1
        self.target_numbers = []
        self.round_responded = set()
        self.join_message = None
        self.current_view = None

class JoinButton(Button):
    def __init__(self, game):
        super().__init__(label="انضم للعبة", style=discord.ButtonStyle.green, custom_id="join_button")
        self.game = game

    async def callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)

            if not self.game.is_active:
                await interaction.followup.send("اللعبة غير متاحة حالياً!", ephemeral=True)
                return

            if interaction.user.id in self.game.players:
                await interaction.followup.send("أنت منضم للعبة بالفعل!", ephemeral=True)
                return

            self.game.players.add(interaction.user.id)
            self.game.active_players.add(interaction.user.id)

            players_list = "\n".join([
                f"• {interaction.guild.get_member(player_id).display_name}"
                for player_id in self.game.players
                if interaction.guild.get_member(player_id) is not None
            ])

            embed = discord.Embed(
                title=f"🎮 {BOT_NAME} - اللاعبين المنضمين",
                description=players_list if players_list else "لا يوجد لاعبين حالياً",
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"عدد اللاعبين: {len(self.game.players)} | تم التطوير بواسطة {BOT_OWNER}")

            await interaction.followup.send("تم انضمامك للعبة بنجاح!", ephemeral=True)
            if self.game.join_message:
                await self.game.join_message.edit(embed=embed)

        except Exception as e:
            print(f"Error in JoinButton callback: {e}")
            await interaction.followup.send("حدث خطأ أثناء الانضمام، حاول مرة أخرى.", ephemeral=True)

class NumberButton(Button):
    def __init__(self, number, game):
        super().__init__(
            label=str(number),
            style=discord.ButtonStyle.primary,
            custom_id=f"number_{number}"
        )
        self.number = number
        self.game = game

    async def callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)

            if not self.game.is_active:
                await interaction.followup.send("اللعبة غير نشطة حالياً!", ephemeral=True)
                return

            if interaction.user.id not in self.game.active_players:
                await interaction.followup.send("لا يمكنك المشاركة في هذه الجولة!", ephemeral=True)
                return

            if interaction.user.id in self.game.round_responded:
                await interaction.followup.send("لقد قمت باختيار رقم بالفعل في هذه الجولة!", ephemeral=True)
                return

            self.game.round_responded.add(interaction.user.id)

            if self.number in self.game.target_numbers:
                await interaction.followup.send("إجابة صحيحة! ستنتقل للجولة التالية!", ephemeral=True)
            else:
                self.game.active_players.remove(interaction.user.id)
                await interaction.followup.send("إجابة خاطئة! لقد خرجت من اللعبة!", ephemeral=True)
                await interaction.message.channel.send(f"{interaction.user.mention} خرج من اللعبة!")

        except Exception as e:
            print(f"Error in NumberButton callback: {e}")
            await interaction.followup.send("حدث خطأ أثناء معالجة اختيارك، حاول مرة أخرى.", ephemeral=True)

class GameView(View):
    def __init__(self, game):
        super().__init__(timeout=None)
        self.game = game
        for i in range(1, 11):
            self.add_item(NumberButton(i, game))

async def check_game_status(ctx: commands.Context, game: NumberGame) -> bool:
    try:
        if len(game.active_players) == 0:
            await ctx.send("جميع اللاعبين خسروا! انتهت اللعبة.")
            game.reset()
            return False
        elif len(game.active_players) == 1:
            winner_id = list(game.active_players)[0]
            winner = ctx.guild.get_member(winner_id)
            if winner:
                await ctx.send(f"🎉 تهانينا! {winner.mention} هو الفائز!")
            game.reset()
            return False
        return True
    except Exception as e:
        print(f"Error in check_game_status: {e}")
        await ctx.send("حدث خطأ أثناء التحقق من حالة اللعبة.")
        game.reset()
        return False

game = NumberGame()

@bot.command(name='start')
@commands.cooldown(1, 30, commands.BucketType.guild)
async def start_game(ctx: commands.Context):
    try:
        if game.is_active:
            await ctx.send("هناك لعبة جارية بالفعل!")
            return

        game.reset()
        game.is_active = True

        intro_embed = discord.Embed(
            title=f"🎲 مرحباً بك في {BOT_NAME}",
            description="اختر رقمين صحيحين من 1 إلى 10 للتأهل للمرحلة التالية!",
            color=discord.Color.gold()
        )
        intro_embed.add_field(
            name="📜 قوانين اللعبة",
            value="• لديك 10 ثوانٍ للاختيار في كل جولة\n"
                  "• اختيار رقم خاطئ يعني الخروج من اللعبة\n"
                  "• الفائز هو آخر لاعب متبقي",
            inline=False
        )
        intro_embed.set_footer(text=f"الإصدار {BOT_VERSION} | تم التطوير بواسطة {BOT_OWNER}")
        await ctx.send(embed=intro_embed)

        join_embed = discord.Embed(
            title=f"🎮 {BOT_NAME} - اللاعبين المنضمين",
            description="لم ينضم أي لاعب بعد",
            color=discord.Color.blue()
        )
        join_embed.set_footer(text=f"عدد اللاعبين: 0 | تم التطوير بواسطة {BOT_OWNER}")

        join_view = View(timeout=15)
        join_button = JoinButton(game)
        join_view.add_item(join_button)

        game.join_message = await ctx.send(embed=join_embed, view=join_view)
        await asyncio.sleep(15)

        if len(game.players) < 2:
            await ctx.send("لا يوجد عدد كافٍ من اللاعبين! تم إلغاء اللعبة.")
            game.reset()
            return

        start_embed = discord.Embed(
            title=f"🎮 {BOT_NAME}",
            description=f"بدأت اللعبة مع {len(game.players)} لاعبين!",
            color=discord.Color.green()
        )
        start_embed.set_footer(text=f"تم التطوير بواسطة {BOT_OWNER}")
        await ctx.send(embed=start_embed)

        game_view = GameView(game)
        game.current_view = game_view

        while game.is_active:
            try:
                game.round_responded.clear()
                game.target_numbers = random.sample(range(1, 11), 2)

                round_embed = discord.Embed(
                    title=f"🎲 {BOT_NAME} - الجولة {game.current_round}",
                    description=f"عدد اللاعبين المتبقين: {len(game.active_players)}\nاختر رقماً:",
                    color=discord.Color.green()
                )
                round_embed.set_footer(text=f"تم التطوير بواسطة {BOT_OWNER}")

                round_msg = await ctx.send(embed=round_embed, view=game_view)
                await asyncio.sleep(10)

                non_responded = game.active_players - game.round_responded
                for player_id in non_responded:
                    if player_id in game.active_players:  # تحقق إضافي
                        game.active_players.remove(player_id)
                        player = ctx.guild.get_member(player_id)
                        if player:  # تحقق من وجود اللاعب
                            await ctx.send(f"{player.mention} تم إقصاؤه لعدم الاستجابة!")

                try:
                    await round_msg.edit(view=None)
                except discord.NotFound:
                    pass

                if not await check_game_status(ctx, game):
                    break

                game.current_round += 1

                numbers_embed = discord.Embed(
                    title="🎯 الأرقام الصحيحة",
                    description=f"الأرقام الصحيحة كانت: {game.target_numbers}",
                    color=discord.Color.orange()
                )
                numbers_embed.set_footer(text=f"تم التطوير بواسطة {BOT_OWNER}")
                await ctx.send(embed=numbers_embed)
                await asyncio.sleep(3)

            except Exception as e:
                print(f"Error in game loop: {e}")
                await ctx.send("حدث خطأ أثناء اللعب. جاري إعادة تشغيل اللعبة...")
                game.reset()
                break

    except Exception as e:
        print(f"Error in start_game command: {e}")
        await ctx.send("حدث خطأ أثناء بدء اللعبة. حاول مرة أخرى.")
        game.reset()

@start_game.error
async def start_game_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"يرجى الانتظار {int(error.retry_after)} ثانية قبل بدء لعبة جديدة.")

@bot.event
async def on_ready():
    print(f"""
╔════════════════════════════════════════╗
║ {BOT_NAME} Bot is now running!
║ Version: {BOT_VERSION}
║ Developer: {BOT_OWNER}
║ Bot Name: {bot.user}
╚════════════════════════════════════════╝
""")
    await bot.change_presence(activity=discord.Game(name=f"{BOT_NAME} | !start"))

bot.run('')
