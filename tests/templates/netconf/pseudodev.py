# This test lacks real Netconf emulation but it's sufficient to test RPC parsing.
commands = (
    (
        """
<get xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">

    <filter>abc</filter>

</get>
""".strip(),
        """
<data>abc</data>
""",
    ),
)
