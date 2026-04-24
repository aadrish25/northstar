from memory.resource_normalizers import normalize_resource
from memory.resource_normalizers import normalize_youtube_video
from memory.resource_normalizers import normalize_book

def get_tool_query(tool, context: dict):
    aliases = getattr(tool, "query_aliases", ())
    for key in aliases:
        value = context.get(key)
        if value:
            return value
    return context.get("user_input")


def get_tool_items(tool, result: dict):
    items_key = getattr(tool, "result_items_key", "items")
    # print(f"\n\n[TOOL EXECUTOR] Extracting items with key '{items_key}'\n")
    return result.get(items_key, []) if isinstance(result, dict) else []

async def execute_tool_with_feedback(
    user_id: str,
    tool,
    context: dict,
    tool_cache,
    user_recommended_memory,
    feedback_agent
):
    # print(f"\n\n[TOOL EXECUTOR]")
    tool_id = getattr(tool, "__name__", str(tool))
    # print(f"\n\n[TOOL EXECUTOR]Attempting to execute tool: {tool_id} \n")
    query = get_tool_query(tool, context)
    # print(f"\n\n[TOOL EXECUTOR] Query: {query} \n")
    cache_key = f"{tool_id}"
    
    action = context.get("feedback_decision", {}).get("action")
    refined_query = context.get("feedback_decision", {}).get("refined_query")

    # -----------------------
    # CHECK CACHE
    # -----------------------
    cached = tool_cache.get(user_id, cache_key)
    # print(f"\n\n[TOOL EXECUTOR] Tool cache: {cached}\n")

    if cached and action == "save":
        context.update(cached)

        cached_full = tool_cache.get_full(user_id, cache_key) or {}
        # print(f"\n\n[TOOL EXECUTOR] Cached full entry: {cached_full}\n")
        cached_query = (cached_full.get("meta") or {}).get("query")
        # print(f"\n\n[TOOL EXECUTOR] Cached query: {cached_query}\n")
        context["previous_query"] = cached_query or query
        # print(f"\n\n[TOOL EXECUTOR] Context before feedback agent: {context['previous_query']}\n")
        context["items"] = get_tool_items(tool, cached)
        # print(f"\n\n[TOOL EXECUTOR] Cached items: {context['items']}\n")

        # decision = await feedback_agent.run(context)
        # # print(f"\n\n[TOOL EXECUTOR] Feedback agent decision: {decision}\n")

        # action = decision.get("action")
        # refined_query = decision.get("refined_query")
        

        # print(f"\n\n[TOOL EXECUTOR] Action: {action}, Refined query: {refined_query}\n")
        
        # -----------------------
        # SAVE (FINAL USER CONFIRM)
        # -----------------------
        if action == "save":
            result = cached_full.get("result", {})

            items = get_tool_items(tool, result)
            # print(f"\n\n[TOOL EXECUTOR] Items to save: {items}\n")
            # Prefer tool metadata over result['type'] (tools are inconsistent: book/books, etc.)
            item_type = getattr(tool, "resource_type", None) or result.get("type")
            # print(f"\n\n[TOOL EXECUTOR] Item type: {item_type}\n")
            normalized = []

            for item in items:
                try:
                    # Backwards compatibility for existing video/book normalizers, but route all
                    # other types through the central dispatcher so we always produce an `id`.
                    if item_type == "video":
                        normalized.append(normalize_youtube_video(item))
                    elif item_type in {"book", "books"}:
                        normalized.append(normalize_book(item))
                    else:
                        normalized.append(normalize_resource(item, kind=item_type))
                except Exception as e:
                    # print("exception in storing",e)
                    continue

            if normalized:
                user_recommended_memory.upsert(user_id, normalized)
                
            
            return

        # -----------------------
        # REFINE QUERY
        # -----------------------
        if action == "refine" and refined_query:
            query_key = getattr(tool, "query_key", None)

            if query_key:
                context[query_key] = refined_query

            refined_cache_key = f"{tool_id}"

            refined_cached = tool_cache.get(user_id, refined_cache_key)

            if refined_cached:
                context.update(refined_cached)
                return

            result = await tool(context)
            tool_cache.set(
                user_id,
                refined_cache_key,
                result,
                meta={
                    "query": refined_query,
                    "resource_type": getattr(tool, "resource_type", None),
                },
            )

            if isinstance(result, dict):
                context.update(result)

            return

        # -----------------------
        # DEFAULT: REUSE
        # -----------------------
        return

    # -----------------------
    # FIRST FETCH
    # -----------------------
    result = await tool(context)

    tool_cache.set(
        user_id,
        cache_key,
        result,
        meta={
            "query": query,
            "resource_type": getattr(tool, "resource_type", None),
        },
    )

    if isinstance(result, dict):
        context.update(result)