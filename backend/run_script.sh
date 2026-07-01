#!/bin/bash
# run_script.sh - Dynamic interactive runner for backend scripts and seeders

clear

echo "========================================================"
echo " 🌊 Nile Basin Wetland Platform - Backend Script Runner"
echo "========================================================"
echo ""

# Find runnable python files under app/scripts and app/seeds
# Excludes __init__.py and helper files
files=($(find app/scripts app/seeds -name "*.py" ! -name "__init__.py" \( ! -name "*helper.py" -o -name "form_seeder_helper.py" \) | sort))

if [ ${#files[@]} -eq 0 ]; then
  echo "No runnable scripts found."
  exit 1
fi

echo "Select a script to run:"
for i in "${!files[@]}"; do
  path="${files[$i]}"
  # Convert relative path to python module format (e.g. app/scripts/create_user.py -> app.scripts.create_user)
  module=$(echo "$path" | sed 's/\.py$//' | sed 's/\//\./g')
  echo "$((i+1))) $module ($path)"
done
exit_option=$(( ${#files[@]} + 1 ))
echo "${exit_option}) Exit"
echo ""

read -p "Enter choice [1-${exit_option}]: " choice
echo ""

if [ "$choice" -eq "${exit_option}" ]; then
  echo "👋 Exiting."
  exit 0
elif [ "$choice" -ge 1 ] && [ "$choice" -le "${#files[@]}" ]; then
  selected_file="${files[$((choice-1))]}"
  module=$(echo "$selected_file" | sed 's/\.py$//' | sed 's/\//\./g')
  echo "🚀 Running: python -m $module..."
  python -m "$module"
else
  echo "❌ Invalid choice."
  exit 1
fi
