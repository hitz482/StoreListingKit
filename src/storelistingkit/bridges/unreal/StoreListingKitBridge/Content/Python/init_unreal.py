"""Runs automatically when the editor loads this plugin (requires the Python Editor Script Plugin)."""

import unreal

try:
    import slk_bridge

    slk_bridge.register_menus()
except Exception as exc:  # never break editor startup
    unreal.log_warning(f"Store Listing Kit bridge failed to load: {exc}")
