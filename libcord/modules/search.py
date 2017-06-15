from libcord.libcord import LibCord, CommandHandler

def init(cord: LibCord):
    search: CommandHandler = cord.create_handler('search')

    @search.register("g")
    def google(s: str):
        """google something"""
        print(f"google {s} v4")
