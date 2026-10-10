from pyrogram import Client

api_id = int(input("Enter your API ID: "))
api_hash = input("Enter your API HASH: ")

with Client(
    "aura_session",
    api_id=api_id,
    api_hash=api_hash,
    in_memory=True
) as app:
    print("\nYour String Session:\n")
    print(app.export_session_string())