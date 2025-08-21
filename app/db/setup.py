async def setup_indexes():
    try:
        # Create indexes for better query performance
        teams_collection = db['teams']
        await teams_collection.create_index([
            ("members.user_id", 1),
            ("hack_id", 1)
        ])
        
        events_collection = db['events']
        await events_collection.create_index("hack_id")
        
    except Exception as e:
        print(f"Error setting up indexes: {str(e)}")