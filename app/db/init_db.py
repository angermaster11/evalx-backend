async def init_indexes():
    try:
        # Teams collection indexes
        teams_collection = db['teams']
        await teams_collection.create_index([
            ("members.user_id", 1),
            ("hack_id", 1)
        ])

        # Events collection indexes
        events_collection = db['events']
        await events_collection.create_index("hack_id", unique=True)

    except Exception as e:
        print(f"Error creating indexes: {str(e)}")