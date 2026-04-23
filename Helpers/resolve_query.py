def resolve_query(context: dict, *keys):
    for key in keys:
        value = context.get(key)
        if value:
            return value
    return None
