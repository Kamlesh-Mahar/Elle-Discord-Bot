import discord
from discord import app_commands
import requests
import json

TOKEN = ""  # Replace with your actual bot token
ANILIST_API_URL = "https://graphql.anilist.co"
JIKAN_API_URL = "https://api.jikan.moe/v4/characters"
WAIFU_IM_API_URL = "https://api.waifu.im/sfw/waifu/"
WAIFU_IT_API_URL = "https://waifu.it/api/waifu/search?q="

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


def truncate(text, max_length=1024):
  return text if len(text) <= max_length else text[:1021] + "..."


# Function to fetch waifu details from AniList
def get_waifu_details(name):
  query = """
    query ($search: String) {
      Character(search: $search) {
        name {
          full
        }
        age
        gender
        dateOfBirth {
          year
          month
          day
        }
        description
        image {
          large
        }
        siteUrl
        media {
          nodes {
            title {
              romaji
            }
          }
        }
      }
    }
    """
  variables = {"search": name}
  try:
    response = requests.post(ANILIST_API_URL,
                             json={
                                 "query": query,
                                 "variables": variables
                             })
    data = response.json()
    if "errors" in data or not data.get("data", {}).get("Character"):
      return get_waifu_from_jikan(name) or get_waifu_from_waifu_im(
          name) or get_waifu_from_waifu_it(name)
    character = data["data"]["Character"]
    if character.get("gender", "").lower() != "female":
      return None  # Ignore male characters
    return character
  except Exception as e:
    print(f"Error fetching waifu details: {e}")
    return get_waifu_from_jikan(name) or get_waifu_from_waifu_im(
        name) or get_waifu_from_waifu_it(name)


# Function to fetch waifu details from Jikan (MAL API)
def get_waifu_from_jikan(name):
  try:
    response = requests.get(f"{JIKAN_API_URL}?q={name}")
    data = response.json()
    if data and "data" in data and len(data["data"]) > 0:
      for character in data["data"]:
        if character.get(
            "name", "").lower() == name.lower() and character.get("mal_id"):
          return {
              "name": {
                  "full": character["name"]
              },
              "age":
              "Unknown",
              "gender":
              "Female",
              "description":
              truncate(character.get("about", "No description available.")),
              "image": {
                  "large": character["images"]["jpg"]["image_url"]
              },
              "siteUrl":
              character.get("url", ""),
              "media": {
                  "nodes": [{
                      "title": {
                          "romaji": "Unknown"
                      }
                  }]
              }
          }
    return None
  except Exception as e:
    print(f"Jikan API Error: {e}")
    return None


# Fallback API (Waifu.im)
def get_waifu_from_waifu_im(name):
  try:
    response = requests.get(f"{WAIFU_IM_API_URL}?query={name}")
    data = response.json()
    if data and "images" in data:
      waifu = data["images"][0]
      return {
          "name": {
              "full": name
          },
          "age": "Unknown",
          "gender": "Female",
          "description": "Unknown",
          "image": {
              "large": waifu["url"]
          },
          "siteUrl": "",
          "media": {
              "nodes": [{
                  "title": {
                      "romaji": "Unknown"
                  }
              }]
          }
      }
    return None
  except Exception as e:
    print(f"Waifu.im API Error: {e}")
    return None


# Waifu.it API
def get_waifu_from_waifu_it(name):
  try:
    response = requests.get(f"{WAIFU_IT_API_URL}{name}")
    data = response.json()
    if data and "results" in data and len(data["results"]) > 0:
      waifu = data["results"][0]
      return {
          "name": {
              "full": waifu["name"]
          },
          "age": "Unknown",
          "gender": "Female",
          "description": "Unknown",
          "image": {
              "large": waifu["image_url"]
          },
          "siteUrl": "",
          "media": {
              "nodes": [{
                  "title": {
                      "romaji": "Unknown"
                  }
              }]
          }
      }
    return None
  except Exception as e:
    print(f"Waifu.it API Error: {e}")
    return None


@tree.command(name="waifu",
              description="Get details about your favorite anime waifu")
async def waifu(interaction: discord.Interaction, name: str):
  await interaction.response.defer()
  character = get_waifu_details(name)
  if not character:
    await interaction.followup.send(
        "❌ Waifu not found or not a female character! Please check the spelling and try again."
    )
    return

  embed = discord.Embed(title=character["name"]["full"],
                        url=character.get("siteUrl", ""),
                        color=discord.Color.pink())
  embed.set_image(url=character["image"].get("large", ""))
  embed.add_field(name="Age",
                  value=character.get("age", "Unknown"),
                  inline=True)
  embed.add_field(name="Gender",
                  value=character.get("gender", "Unknown"),
                  inline=True)
  embed.add_field(name="Description",
                  value=truncate(
                      character.get("description",
                                    "No description available.")),
                  inline=False)

  if "media" in character and "nodes" in character["media"]:
    anime_titles = ", ".join([
        anime["title"]["romaji"] for anime in character["media"]["nodes"]
        if "title" in anime
    ])
    embed.add_field(name="Anime Appearances",
                    value=truncate(anime_titles or "Unknown"),
                    inline=False)

  await interaction.followup.send(embed=embed)


@client.event
async def on_ready():
  await tree.sync()
  print(f'✅ Logged in as {client.user}')


client.run(TOKEN)
