# app/tools/__init__.py

from .open_app import open_app
from .get_time import get_time
from .search_wikipedia import search_wikipedia
from .run_python import run_python
from .open_browser import open_browser_and_search

# Enhanced context-aware tools
from .get_recent_files import get_recent_files
from .session_manager import (
    save_current_session, restore_session, list_sessions, delete_session,
    create_workspace_template, setup_workspace
)
from .smart_shortcuts import (
    execute_shortcut, list_shortcuts, create_shortcut_from_template,
    start_recording_shortcut, record_action, stop_recording_shortcut,
    delete_shortcut, get_available_templates
)
from .context_resolver import (
    resolve_query, add_context_shortcut, list_context_shortcuts,
    remove_context_shortcut, get_user_preferences, update_user_preference,
    get_context_suggestions, learn_from_interaction
)
from .system_suggestions import (
    get_system_suggestions, dismiss_suggestion, execute_automated_suggestion,
    run_health_check, get_suggestions_summary, get_suggestions_by_type,
    get_actionable_suggestions
)

# High-priority system management tools
from .file_manager import (
    create_folder, delete_file_or_folder, move_file_or_folder, copy_file_or_folder,
    find_files, get_file_info, list_directory
)
from .process_manager import (
    list_running_apps, get_process_info, close_application, get_system_resources,
    set_process_priority, launch_application
)
from .window_manager import (
    list_windows, find_window, focus_window, minimize_window, maximize_window,
    restore_window, resize_window, move_window, close_window, arrange_windows,
    get_window_info
)
from .system_control import (
    shutdown_system, restart_system, cancel_shutdown, lock_screen, sleep_system,
    get_volume_level, set_volume_level, mute_system, get_system_info,
    run_command_as_admin, create_system_restore_point
)
