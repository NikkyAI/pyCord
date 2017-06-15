from libcord.libcord import LibCord, Command, ResultType
from importlib import reload

def init(cord: LibCord):
    # config = None
    # with open('config.yaml') as f: 
    #     config = yaml.load(f)
    # print(yaml.dump(config))
    # cord: LibCord = LibCord(**config['core'])

    core = cord.create_handler('core')

    @core.register("list")
    def list_function():
        """
        lists all registered commands.
        """
        for group, cmd_group in cord.cmd_handlers.items():
            print(group.upper())
            for key, cmd in cmd_group.cmd_map.items():
                desc = ""
                if cmd.parser.description:
                    desc = ": " +cmd.parser.description
                print(f"\t{key}{desc}")

    @core.register("help")
    def help_function(command: str):
        """
        lists all registered commands.
        """
        cmd: Command = None
        for handler_name, cmd_handler in cord.cmd_handlers.items():
            if command in cmd_handler.cmd_map:
                cmd = cmd_handler.cmd_map[command]
                break

        if not cmd:
            print(f"no function {command} found")
            return

        cmd.parser.print_help();
        return ResultType.HELP

    @core.register("reload")
    def reload_function(module: str):
        """
        reloads a module.
        """
        cord.loader.reload(module)
        print(f"reloaded {module}")
        # for group, cmd_group in cord.cmd_handlers.items():
        #     print(group.upper())
        #     for key, cmd in cmd_group.cmd_map.items():
        #         print(f"\tcommand {key}: {cmd}")
