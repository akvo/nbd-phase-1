class USSDDynamicPager:
    def __init__(self, page_size=4):
        self.page_size = page_size

    def render_page(
        self,
        items,
        inputs_for_question,
        prompt_title,
        lang="en",
        is_cascade=False,
    ):
        """
        Calculates page number, slices the list, and appends dynamic
        navigation options automatically based on list length.
        """
        page = 0
        max_pages = (len(items) - 1) // self.page_size + 1
        consumed = 0

        # Traverse input state for this question
        for val in inputs_for_question:
            consumed += 1
            clean_val = val.strip()
            if clean_val == "98" and page < max_pages - 1:
                page += 1
            elif clean_val == "0" and page > 0:
                page -= 1
            else:
                try:
                    choice = int(clean_val) - 1
                    actual_idx = page * self.page_size + choice
                    if 0 <= actual_idx < len(items):
                        return {
                            "selected": items[actual_idx],
                            "consumed": consumed,
                            "final_value": str(actual_idx + 1),
                            "actual_idx": actual_idx,
                        }
                except ValueError:
                    pass

        # If not selected yet, slice list and generate screen prompt
        start_idx = page * self.page_size
        page_slice = items[start_idx : start_idx + self.page_size]  # noqa

        menu_lines = [prompt_title]
        current_parent_id = None
        for idx, item in enumerate(page_slice, start_idx + 1):
            if is_cascade:
                # Grouping under Region/Mkoa headers
                if item.parent_id != current_parent_id:
                    current_parent_id = item.parent_id
                    parent = item.parent
                    if parent:
                        if len(menu_lines) > 1 or (
                            len(menu_lines) == 1 and menu_lines[0]
                        ):
                            menu_lines.append("")
                        menu_lines.append(
                            f"{parent.name} (Mkoa):"
                            if lang == "sw"
                            else f"{parent.name} (Region):"
                        )
                screen_idx = idx - start_idx
                menu_lines.append(f"  {screen_idx}. {item.name}")
            else:
                name = getattr(item, "label", getattr(item, "name", str(item)))
                screen_idx = idx - start_idx
                menu_lines.append(f"{screen_idx}: {name}")

        # Paging options matching exactly "98: View More" and "0: Back" formats
        if page < max_pages - 1:
            if is_cascade:
                menu_lines.append(
                    "  98. Angalia zaidi"
                    if lang == "sw"
                    else "  98. View More"
                )
            else:
                menu_items_vm = (
                    "98: Angalia zaidi" if lang == "sw" else "98: View More"
                )
                menu_lines.append(menu_items_vm)
        if page > 0:
            if is_cascade:
                menu_lines.append(
                    "  0. Rudi nyuma" if lang == "sw" else "  0. Back"
                )
            else:
                menu_items_back = (
                    "0: Rudi nyuma" if lang == "sw" else "0: Back"
                )
                menu_lines.append(menu_items_back)

        return {
            "selected": None,
            "prompt_text": "\n".join(menu_lines),
            "consumed": consumed,
        }
