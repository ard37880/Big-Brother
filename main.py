import nextcord
import os
import re

from nextcord.ext import commands
from nextcord import Interaction, SlashOption, utils  
from words import words
from datetime import datetime, timedelta, timezone
from apikeys import discord_key


intents = nextcord.Intents.default()
intents.messages = True
intents.message_content = True
intents.reactions = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

voice_channel_join_times = {}
log_channel_id = #YOUR LOG CHANNEL HERE
profanity_list = words


@bot.event
async def on_ready():
    print(f"{bot.user} is now running and ready to log!")

async def log_to_channel(embed: nextcord.Embed):
    channel = bot.get_channel(log_channel_id)
    if channel:
        try:
            await channel.send(embed=embed)
        except nextcord.Forbidden:
            print(f"Failed to send message: Missing access to channel {channel.id}")
        except nextcord.HTTPException as e:
            print(f"Failed to send message due to HTTP error: {e}")
    else:
        print(f"Log channel with ID {log_channel_id} could not be found.")

def log_command_usage(func):
    async def wrapper(interaction: nextcord.Interaction, *args, **kwargs):
        command_name = func.__name__
        description = f"{interaction.user} used slash command '{command_name}' in {interaction.channel} at {interaction.created_at}."
        embed = nextcord.Embed(title="Slash Command Used", description=description, color=nextcord.Color.blue())
        await log_to_channel(embed)
        await func(interaction, *args, **kwargs)
    return wrapper

@bot.event
async def on_message(message: nextcord.Message):
    if message.author == bot.user or message.guild is None:
        return

    if any(profane_word in message.content.lower() for profane_word in profanity_list):
        message_link = f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}"

        embed = nextcord.Embed(title="Profanity Alert", color=nextcord.Color.red())
        embed.add_field(name="User", value=message.author.mention, inline=True)
        embed.add_field(name="Channel", value=message.channel.mention, inline=True)
        embed.add_field(name="Message Link", value=f"[Go to Message]({message_link})", inline=False)
        embed.add_field(name="Message Content", value=message.content, inline=False)
        
        await log_to_channel(embed)

    await bot.process_commands(message)

@bot.event
async def on_message_delete(message: nextcord.Message):
    if message.author == bot.user or message.guild is None:
        return 

    description = f"A message by {message.author.mention} was deleted in {message.channel.mention}."
    embed = nextcord.Embed(title="Message Deleted", description=description, color=nextcord.Color.orange())

    if message.content:
        embed.add_field(name="Deleted Message Content", value=message.content, inline=False)

    if message.attachments:
        attachments = '\n'.join(attachment.url for attachment in message.attachments)
        embed.add_field(name="Attachments", value=attachments, inline=False)

    await log_to_channel(embed)

@bot.event
async def on_message_edit(before: nextcord.Message, after: nextcord.Message):
    if before.content == after.content or after.author.bot:
        return

    message_link = f"https://discord.com/channels/{after.guild.id}/{after.channel.id}/{after.id}"

    embed = nextcord.Embed(title="Message Edited", color=nextcord.Color.yellow(), url=message_link)
    embed.add_field(name="User", value=after.author.mention, inline=True)
    embed.add_field(name="Channel", value=after.channel.mention, inline=True)
    embed.add_field(name="Message Link", value=f"[Jump to Message]({message_link})", inline=False)

    before_content = before.content[:1021] + '...' if len(before.content) > 1024 else before.content
    after_content = after.content[:1021] + '...' if len(after.content) > 1024 else after.content

    embed.add_field(name="Before", value=before_content or "No text content", inline=False)
    embed.add_field(name="After", value=after_content or "No text content", inline=False)

    await log_to_channel(embed)

@bot.event
async def on_member_join(member: nextcord.Member):
    account_age = datetime.now(timezone.utc) - member.created_at
    joined_at = member.joined_at.strftime('%m/%d/%Y %H:%M:%S') if member.joined_at else 'Unknown'

    embed = nextcord.Embed(title="Member Joined", description=f"{member.mention} joined the server.", color=nextcord.Color.green())
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    embed.add_field(name="Joined Server", value=joined_at, inline=True)
    embed.add_field(name="Account Age", value=f"{account_age.days} days", inline=True)
    embed.add_field(name="Standing", value="New Member", inline=True)

    await log_to_channel(embed)


@bot.event
async def on_member_remove(member: nextcord.Member):
    if member.joined_at:  
        duration_in_server = datetime.now(timezone.utc) - member.joined_at
        stay_duration = f"{duration_in_server.days} days"
    else:
        stay_duration = "Unknown"

    left_at = datetime.now(timezone.utc).strftime('%m/%d/%Y %H:%M:%S')

    embed = nextcord.Embed(title="Member Left", description=f"{member.display_name} left the server.", color=nextcord.Color.orange())
    embed.set_thumbnail(url=member.display_avatar.url)  
    embed.add_field(name="Stay Duration", value=stay_duration, inline=True)
    embed.add_field(name="Left At", value=left_at, inline=True)

    await log_to_channel(embed)

@bot.event
async def on_member_update(before: nextcord.Member, after: nextcord.Member):
    roles_added = [role for role in after.roles if role not in before.roles]
    roles_removed = [role for role in before.roles if role not in after.roles]
    
    if roles_added or roles_removed:
        embed = nextcord.Embed(title="Role Update", description=f"Member: {after.mention}", color=nextcord.Color.blue())

        embed.set_thumbnail(url=after.avatar.url if after.avatar else after.default_avatar.url)

        if roles_added:
            roles_added_str = '\n'.join(f":white_check_mark: {role.name}" for role in roles_added)
            embed.add_field(name="Roles Added", value=roles_added_str, inline=False)

        if roles_removed:
            roles_removed_str = '\n'.join(f":x: {role.name}" for role in roles_removed)
            embed.add_field(name="Roles Removed", value=roles_removed_str, inline=False)
        
        await log_to_channel(embed)

@bot.event
async def on_voice_state_update(member: nextcord.Member, before: nextcord.VoiceState, after: nextcord.VoiceState):
    utc_now = datetime.now(timezone.utc)

    if before.channel is None and after.channel is not None:
        voice_channel_join_times[member.id] = utc_now
        embed = nextcord.Embed(title="Joined Voice Channel", color=nextcord.Color.green())
        embed.add_field(name="User", value=f"{member.mention} ({member.display_name})", inline=False)
        embed.add_field(name="Channel", value=after.channel.name, inline=False)
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        embed.set_footer(text=f"Joined at {utc_now.strftime('%m/%d/%Y %H:%M:%S')} UTC")
        await log_to_channel(embed)

    elif before.channel is not None and after.channel is None:
        join_time = voice_channel_join_times.pop(member.id, None)
        if join_time:
            duration = utc_now - join_time
            duration_str = str(duration).split('.')[0]  
        else:
            duration_str = "Unknown"
        
        embed = nextcord.Embed(title="Left Voice Channel", color=nextcord.Color.red())
        embed.add_field(name="User", value=f"{member.mention} ({member.display_name})", inline=False)
        embed.add_field(name="Channel", value=before.channel.name, inline=False)
        embed.add_field(name="Duration in Channel", value=duration_str, inline=False)
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        embed.set_footer(text=f"Left at {utc_now.strftime('%m/%d/%Y %H:%M:%S')} UTC")
        await log_to_channel(embed)
    
    elif before.channel != after.channel:
        pass

@bot.event
async def on_guild_channel_create(channel):
    embed = nextcord.Embed(title="Channel Created", description=f"**{channel.name}** was created.", color=nextcord.Color.green())
    embed.set_footer(text=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'))

    try:
        audit_logs = await channel.guild.audit_logs(limit=1, action=nextcord.AuditLogAction.channel_create).flatten()
        if audit_logs:
            user = audit_logs[0].user
            embed.set_author(name=f"{user.name}#{user.discriminator}", icon_url=user.avatar.url if user.avatar else user.default_avatar.url)
    except Exception as e:
        print(f"Failed to fetch audit log for channel creation: {e}")
    
    await log_to_channel(embed)

@bot.event
async def on_guild_channel_delete(channel):
    embed = nextcord.Embed(title="Channel Deleted", description=f"**{channel.name}** was deleted.", color=nextcord.Color.red())
    embed.set_footer(text=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'))

    try:
        audit_logs = await channel.guild.audit_logs(limit=1, action=nextcord.AuditLogAction.channel_delete).flatten()
        if audit_logs:
            user = audit_logs[0].user
            embed.set_author(name=f"{user.name}#{user.discriminator}", icon_url=user.avatar.url if user.avatar else user.default_avatar.url)
    except Exception as e:
        print(f"Failed to fetch audit log for channel deletion: {e}")
    
    await log_to_channel(embed)

@bot.event
async def on_guild_channel_update(before, after):
    embed = nextcord.Embed(title="Channel Updated", color=nextcord.Color.gold())
    embed.set_footer(text=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'))

    if before.name != after.name:
        embed.add_field(name="Change", value="Channel Name", inline=False)
        embed.add_field(name="Before", value=before.name, inline=True)
        embed.add_field(name="After", value=after.name, inline=True)

    if isinstance(before, nextcord.TextChannel) and isinstance(after, nextcord.TextChannel):
        if before.topic != after.topic:
            embed.add_field(name="Change", value="Channel Topic", inline=False)
            embed.add_field(name="Before", value=before.topic or "None", inline=True)
            embed.add_field(name="After", value=after.topic or "None", inline=True)

    try:
        audit_logs = await after.guild.audit_logs(limit=1, action=nextcord.AuditLogAction.channel_update).flatten()
        if audit_logs:
            user = audit_logs[0].user
            embed.set_author(name=f"{user.name}#{user.discriminator}", icon_url=user.avatar.url if user.avatar else user.default_avatar.url)
    except Exception as e:
        print(f"Failed to fetch audit log for channel update: {e}")
    
    embed.add_field(name="Channel", value=after.mention, inline=False)
    await log_to_channel(embed)

bot.run(discord_key)
