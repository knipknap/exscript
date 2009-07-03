from termconnect import otp

def execute(scope, password, seed, seqs):
    return [otp.generate(password[0],
                         seed[0],
                         int(seq),
                         1,
                         'md4',
                         'sixword')[0] for seq in seqs]
