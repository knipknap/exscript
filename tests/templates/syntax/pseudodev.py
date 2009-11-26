commands = (
('ls -1.*', """
hello
testme
"""),

('ls -l .+', lambda x: x)
)
