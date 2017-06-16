from libcord import LibCord, Message, CommandHandler

def init(cord: LibCord):
    test: CommandHandler = cord.create_handler('test')

    @test.register("test")
    @test.argument(dest="args", nargs='+')
    def test_command(args):
        print(f"running test command, args: {args}")

    @test.register(prog="test2")
    @test.argument(dest="name", metavar='NAME')
    def test_command_2(name: str, number: int, random):
        """test number 2, does this end up in --help ?"""
        print("running test command 2, name: " + name)
        print((name + " ") * number)
        print(f"random: {random} {type(random)}")

    @test.register("c")
    def test_context(context: Message):
        print(f"context = { context }")

    @test.register("d")
    def test_defaults(number: int, something: str = None, val: str = "val1"):
        """test the docstring."""
        print(f"testing defaults = number: { number }, something = { something }, val = {val}")

    @test.register("m")
    def test_multiline(i: int):
        """test multiline output."""
        print(f"testing multiline")
        print("\nnewline"*i)

    @test.register("identify")
    def test_auth(context: Message, nick: str):
        """test nickserv"""
        print(f"testing auth module")
        cord.auth.identify(auth_req=AuthRequest(nickname=context.message.username, account=contex.message.account))