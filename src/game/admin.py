from .models.mission import Mission, MissionStage


async def handle_command(command: str, message: str) -> str | None:
    """Handle admin commands sent to the bot."""
    if command == "!new":
        raise ValueError("Use the !new command to create a new mission.")


async def new_mission(mission_id: str) -> Mission:
    """Create a new mission with the given ID."""
    mission = Mission(name=mission_id)
    await mission.init_category()
    await mission.init_stage(MissionStage.INTAKE)
    mission.save()
    return mission
