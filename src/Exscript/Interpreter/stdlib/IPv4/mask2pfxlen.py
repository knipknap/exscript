import util

def execute(scope, masks):
    return [util.mask2pfxlen(mask) for mask in masks]
