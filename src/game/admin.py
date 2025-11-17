from .models.mission import Mission


async def handle_command(command: str, message: str) -> str | None:
    """Handle admin commands sent to the bot."""
    if command == "!new":
        return await new_mission(message)


async def new_mission(mission_id: str) -> str:
    """Create a new mission with the given ID."""
    mission = Mission(name=mission_id, mission=mission_id)
    await mission.init_stage("intake")
    return f"Nieuwe missie '{mission_id}' aangemaakt."
