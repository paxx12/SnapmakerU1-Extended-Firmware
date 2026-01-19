#!/bin/bash
# Patch workflow helper - assists in creating sequential patches for overlays
#
# This script helps manage the complexity of creating patches that build on top of
# previous patches by maintaining a single working directory with all patches applied.

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
WORK_DIR="$ROOT_DIR/tmp/patch-work"
TEMP_DIR="$ROOT_DIR/tmp/patch-work-temp"
FIRMWARE_DIR="$ROOT_DIR/tmp/extracted"

show_help() {
  cat <<EOF
Patch Workflow Helper

Usage: $0 <command> [args]

Commands:
  init <overlay-name>
      Initialize a patch workspace for an overlay.
      Extracts rootfs and applies all existing patches.
      Automatically resets workspace if it already exists.

  save <overlay-name> <patch-name> <files...>
      Save a new patch with changes to the specified files.
      Errors if patch already exists (use 'modify' to update).
      Example: save rfid-support 06-add-feature home/lava/klipper/klippy/extras/file.py

  modify <overlay-name> <patch-name> <files...>
      Update an existing patch with changes to the specified files.
      Errors if patch does not exist (use 'save' to create).
      Example: modify rfid-support 06-add-feature home/lava/klipper/klippy/extras/file.py

  diff <overlay-name> [files...]
      Show diff of current changes without saving.

  status <overlay-name>
      Show what files have been modified in the current workspace.

  reset <overlay-name>
      Reset the workspace by reapplying all patches (no confirmation).

  clean
      Remove the entire patch workspace (prompts for confirmation).

Examples:
  # Start working on a new patch for an existing overlay
  $0 init firmware-extended/13-rfid-support

  # Edit files directly in the workspace
  vim tmp/patch-work/home/lava/klipper/klippy/extras/filament_detect.py

  # Check what changed
  $0 status firmware-extended/13-rfid-support
  $0 diff firmware-extended/13-rfid-support home/lava/klipper/klippy/extras/filament_detect.py

  # Save as a new patch
  $0 save firmware-extended/13-rfid-support 06-my-new-feature home/lava/klipper/klippy/extras/filament_detect.py

  # Modify an existing patch
  $0 modify firmware-extended/13-rfid-support 06-my-new-feature home/lava/klipper/klippy/extras/filament_detect.py

EOF
}

# Shared function to extract and apply patches
# Args: $1 = target directory, $2 = overlay name
extract_and_apply_patches() {
  local target_dir="$1"
  local overlay_name="$2"

  # Extract rootfs
  rm -rf "$target_dir"
  unsquashfs -d "$target_dir" "$FIRMWARE_DIR/rk-unpacked/rootfs.img" > /dev/null 2>&1

  # Run pre-scripts if they exist
  local overlay_dir="$ROOT_DIR/overlays/$overlay_name"
  if [[ -d "$overlay_dir/pre-scripts" ]]; then
    for scriptfile in "$overlay_dir/pre-scripts/"*.sh; do
      if [[ -f "$scriptfile" ]]; then
        bash "$scriptfile" "$target_dir" > /dev/null 2>&1
      fi
    done
  fi

  # Apply patches in alphabetical order
  local patch_dir="$ROOT_DIR/overlays/$overlay_name/patches"
  if [[ -d "$patch_dir" ]]; then
    for patch_file in "$patch_dir"/*.patch; do
      if [[ ! -f "$patch_file" ]]; then
        continue
      fi

      # Apply patch directly to the target directory
      # -p1 strips the first directory component (rootfs.original/ -> home/...)
      set +e
      cd "$target_dir"
      patch -p1 < "$patch_file" 2>&1 | grep -v "patching file" || true
      patch_result=$?
      cd - > /dev/null
      set -e

      if [[ $patch_result -ne 0 ]]; then
        echo "Error: Failed to apply patch $(basename "$patch_file")"
        exit 1
      fi
    done
  fi
}

# Shared function to extract and apply patches, excluding one specific patch
# Args: $1 = target directory, $2 = overlay name, $3 = patch name to skip (without .patch extension)
extract_and_apply_patches_except() {
  local target_dir="$1"
  local overlay_name="$2"
  local skip_patch_name="$3"

  # Extract rootfs
  rm -rf "$target_dir"
  unsquashfs -d "$target_dir" "$FIRMWARE_DIR/rk-unpacked/rootfs.img" > /dev/null 2>&1

  # Run pre-scripts if they exist
  local overlay_dir="$ROOT_DIR/overlays/$overlay_name"
  if [[ -d "$overlay_dir/pre-scripts" ]]; then
    for scriptfile in "$overlay_dir/pre-scripts/"*.sh; do
      if [[ -f "$scriptfile" ]]; then
        bash "$scriptfile" "$target_dir" > /dev/null 2>&1
      fi
    done
  fi

  # Apply patches in alphabetical order, skipping the specified one
  local patch_dir="$ROOT_DIR/overlays/$overlay_name/patches"
  if [[ -d "$patch_dir" ]]; then
    for patch_file in "$patch_dir"/*.patch; do
      if [[ ! -f "$patch_file" ]]; then
        continue
      fi

      # Skip the target patch
      local patch_basename="$(basename "$patch_file" .patch)"
      if [[ "$patch_basename" == "$skip_patch_name" ]]; then
        echo "   Skipping: $skip_patch_name.patch (all subsequent patches will be ignored)"
        break
      fi

      # Apply patch directly to the target directory
      # -p1 strips the first directory component (rootfs.original/ -> home/...)
      set +e
      cd "$target_dir"
      patch -p1 < "$patch_file" 2>&1 | grep -v "patching file" || true
      patch_result=$?
      cd - > /dev/null
      set -e

      if [[ $patch_result -ne 0 ]]; then
        echo "Error: Failed to apply patch $(basename "$patch_file")"
        exit 1
      fi
    done
  fi
}

init_workspace() {
  local overlay_name="$1"

  if [[ -z "$overlay_name" ]]; then
    echo "Error: overlay name required"
    echo "Usage: $0 init <overlay-name>"
    exit 1
  fi

  if [[ ! -d "$ROOT_DIR/overlays/$overlay_name" ]]; then
    echo "Error: Overlay directory not found: overlays/$overlay_name"
    exit 1
  fi

  # Check if we have the extracted firmware
  if [[ ! -d "$FIRMWARE_DIR/rk-unpacked" ]]; then
    echo "Error: No extracted firmware found at tmp/extracted/"
    echo "Please run 'make extract' or 'make build PROFILE=<profile>' first"
    exit 1
  fi

  # Reset workspace if it already exists
  if [[ -d "$WORK_DIR" ]]; then
    echo ">> Workspace already exists - resetting..."
  fi

  echo ">> Initializing patch workspace for $overlay_name..."

  # Extract and apply all patches
  extract_and_apply_patches "$WORK_DIR" "$overlay_name"

  # Save overlay name
  echo "$overlay_name" > "$WORK_DIR/.overlay"

  echo ">> Workspace initialized at $WORK_DIR"
  echo ">> All existing patches have been applied"
  echo ">> You can now edit files in: $WORK_DIR"
}

save_patch() {
  local overlay_name="${1:-$(cat "$WORK_DIR/.overlay" 2>/dev/null)}"
  local patch_name="$2"
  shift 2

  if [[ -z "$patch_name" ]]; then
    echo "Error: patch name required"
    echo "Usage: $0 save <overlay-name> <patch-name> <files...>"
    exit 1
  fi

  if [[ $# -eq 0 ]]; then
    echo "Error: at least one file path required"
    echo "Usage: $0 save <overlay-name> <patch-name> <files...>"
    exit 1
  fi

  if [[ ! -d "$WORK_DIR" ]]; then
    echo "Error: No workspace found. Run: $0 init <overlay-name>"
    exit 1
  fi

  local patch_dir="$ROOT_DIR/overlays/$overlay_name/patches"
  mkdir -p "$patch_dir"

  local patch_file="$patch_dir/$patch_name.patch"

  # Check if patch already exists
  if [[ -f "$patch_file" ]]; then
    echo "Error: Patch already exists: $patch_file"
    echo ""
    echo "To update an existing patch, use:"
    echo "  $0 modify $overlay_name $patch_name <files...>"
    echo ""
    echo "To create a new patch, choose a different patch name."
    exit 1
  fi

  echo ">> Creating patch: $patch_name.patch"
  echo ">> Extracting baseline with all patches applied..."

  # Extract baseline and apply patches
  extract_and_apply_patches "$TEMP_DIR" "$overlay_name"

  # Generate the patch
  {
    for file in "$@"; do
      if [[ -f "$WORK_DIR/$file" ]] || [[ -f "$TEMP_DIR/$file" ]]; then
        echo "   Including: $file"
        diff -Nur "$TEMP_DIR/$file" "$WORK_DIR/$file" || true
      else
        echo "   Warning: File not found: $file"
      fi
    done
  } > "$patch_file"

  # Replace our paths with the standard patch paths
  sed -i.bak "s|$TEMP_DIR/|rootfs.original/|g; s|$WORK_DIR/|rootfs/|g" "$patch_file"
  rm "$patch_file.bak"

  # Clean up temp directory
  rm -rf "$TEMP_DIR"

  echo ">> Patch saved to: $patch_file"
  echo ">> Lines in patch: $(wc -l < "$patch_file")"
  echo ">> Done! You can continue editing in $WORK_DIR"
}

modify_patch() {
  local overlay_name="${1:-$(cat "$WORK_DIR/.overlay" 2>/dev/null)}"
  local patch_name="$2"
  shift 2

  if [[ -z "$patch_name" ]]; then
    echo "Error: patch name required"
    echo "Usage: $0 modify <overlay-name> <patch-name> <files...>"
    exit 1
  fi

  if [[ $# -eq 0 ]]; then
    echo "Error: at least one file path required"
    echo "Usage: $0 modify <overlay-name> <patch-name> <files...>"
    exit 1
  fi

  if [[ ! -d "$WORK_DIR" ]]; then
    echo "Error: No workspace found. Run: $0 init <overlay-name>"
    exit 1
  fi

  local patch_dir="$ROOT_DIR/overlays/$overlay_name/patches"
  local patch_file="$patch_dir/$patch_name.patch"

  # Check if patch exists
  if [[ ! -f "$patch_file" ]]; then
    echo "Error: Patch does not exist: $patch_file"
    echo ""
    echo "To create a new patch, use:"
    echo "  $0 save $overlay_name $patch_name <files...>"
    echo ""
    echo "Available patches in $overlay_name:"
    if [[ -d "$patch_dir" ]]; then
      ls -1 "$patch_dir"/*.patch 2>/dev/null | xargs -n1 basename | sed 's/\.patch$//' | sed 's/^/  - /' || echo "  (no patches found)"
    else
      echo "  (no patches found)"
    fi
    exit 1
  fi

  echo ">> Modifying patch: $patch_name.patch"
  echo ">> Extracting baseline with all patches applied EXCEPT $patch_name..."

  # Extract baseline and apply all patches EXCEPT the one being modified
  extract_and_apply_patches_except "$TEMP_DIR" "$overlay_name" "$patch_name"

  # Generate the patch
  {
    for file in "$@"; do
      if [[ -f "$WORK_DIR/$file" ]] || [[ -f "$TEMP_DIR/$file" ]]; then
        echo "   Including: $file"
        diff -Nur "$TEMP_DIR/$file" "$WORK_DIR/$file" || true
      else
        echo "   Warning: File not found: $file"
      fi
    done
  } > "$patch_file"

  # Replace our paths with the standard patch paths
  sed -i.bak "s|$TEMP_DIR/|rootfs.original/|g; s|$WORK_DIR/|rootfs/|g" "$patch_file"
  rm "$patch_file.bak"

  # Clean up temp directory
  rm -rf "$TEMP_DIR"

  echo ">> Patch modified: $patch_file"
  echo ">> Lines in patch: $(wc -l < "$patch_file")"
  echo ">> Done! You can continue editing in $WORK_DIR"
}

show_status() {
  local overlay_name="${1:-$(cat "$WORK_DIR/.overlay" 2>/dev/null)}"

  if [[ ! -d "$WORK_DIR" ]]; then
    echo "No workspace initialized. Run: $0 init <overlay-name>"
    exit 1
  fi

  echo ">> Creating baseline for comparison..."
  extract_and_apply_patches "$TEMP_DIR" "$overlay_name"

  echo ">> Changed files in workspace:"
  diff -qr "$TEMP_DIR" "$WORK_DIR" 2>/dev/null | grep "Files.*differ" | sed "s|Files $TEMP_DIR/||; s| and $WORK_DIR/.*||" || echo "   (no changes)"

  # Clean up temp directory
  rm -rf "$TEMP_DIR"
}

show_diff() {
  local overlay_name="${1:-$(cat "$WORK_DIR/.overlay" 2>/dev/null)}"
  shift || true

  if [[ ! -d "$WORK_DIR" ]]; then
    echo "No workspace initialized. Run: $0 init <overlay-name>"
    exit 1
  fi

  echo ">> Creating baseline for comparison..."
  extract_and_apply_patches "$TEMP_DIR" "$overlay_name"

  if [[ $# -eq 0 ]]; then
    # Show all diffs
    diff -Nur "$TEMP_DIR" "$WORK_DIR" 2>/dev/null || true
  else
    # Show diffs for specific files
    for file in "$@"; do
      diff -Nur "$TEMP_DIR/$file" "$WORK_DIR/$file" 2>/dev/null || true
    done
  fi

  # Clean up temp directory
  rm -rf "$TEMP_DIR"
}

reset_workspace() {
  local overlay_name="${1:-$(cat "$WORK_DIR/.overlay" 2>/dev/null)}"

  if [[ -z "$overlay_name" ]]; then
    echo "Error: overlay name required or workspace not initialized"
    exit 1
  fi

  echo ">> Resetting workspace (no confirmation)..."

  # Check if we have the extracted firmware
  if [[ ! -d "$FIRMWARE_DIR/rk-unpacked" ]]; then
    echo "Error: No extracted firmware found at tmp/extracted/"
    echo "Please run 'make extract' or 'make build PROFILE=<profile>' first"
    exit 1
  fi

  # Extract and apply all patches
  extract_and_apply_patches "$WORK_DIR" "$overlay_name"

  # Save overlay name
  echo "$overlay_name" > "$WORK_DIR/.overlay"

  echo ">> Workspace reset complete"
  echo ">> All existing patches have been reapplied"
}

clean_workspace() {
  if [[ ! -d "$WORK_DIR" ]] && [[ ! -d "$TEMP_DIR" ]]; then
    echo "No workspace to clean."
    exit 0
  fi

  read -p "Remove patch workspace? This will discard any unsaved changes. (y/N): " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
  fi

  echo ">> Cleaning patch workspace..."
  rm -rf "$WORK_DIR"
  rm -rf "$TEMP_DIR"
  echo ">> Done"
}

# Main command dispatch
case "${1:-help}" in
  init)
    init_workspace "$2"
    ;;
  save)
    shift
    save_patch "$@"
    ;;
  modify)
    shift
    modify_patch "$@"
    ;;
  diff)
    shift
    show_diff "$@"
    ;;
  status)
    show_status "$2"
    ;;
  reset)
    reset_workspace "$2"
    ;;
  clean)
    clean_workspace
    ;;
  help|--help|-h)
    show_help
    ;;
  *)
    echo "Unknown command: $1"
    show_help
    exit 1
    ;;
esac
