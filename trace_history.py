import json

transcript_path = r"C:\Users\JINU\.gemini\antigravity-ide\brain\0b056a11-eec1-4ce5-b05a-820b0eeb3adf\.system_generated\logs\transcript_full.jsonl"

files_to_restore = {
    r"d:\Lenny's Growth Assistant\frontend\src\App.jsx": [],
    r"d:\Lenny's Growth Assistant\frontend\src\components\SessionSidebar.jsx": [],
    r"d:\Lenny's Growth Assistant\frontend\src\index.css": [],
    r"d:\Lenny's Growth Assistant\frontend\tailwind.config.js": [],
    r"d:\Lenny's Growth Assistant\frontend\vite.config.js": []
}

with open(transcript_path, "r", encoding="utf-8") as f:
    for line in f:
        try:
            entry = json.loads(line)
            if entry.get("source") == "MODEL" and entry.get("type") == "PLANNER_RESPONSE":
                # Find tool calls
                if "tool_calls" in entry:
                    for tc in entry["tool_calls"]:
                        name = tc.get("name")
                        args = tc.get("args", {})
                        
                        target_file = None
                        if name == "write_to_file" or name == "replace_file_content" or name == "multi_replace_file_content":
                            target_file = args.get("TargetFile")
                            # Normalize path
                            if target_file:
                                target_file = target_file.strip('"').replace("/", "\\")
                                
                        if target_file in files_to_restore:
                            files_to_restore[target_file].append({
                                "step": entry.get("step_index"),
                                "name": name,
                                "args": args
                            })
        except Exception as e:
            pass

# Output the sequence of modifications for each file so we can see what to restore
for fname, ops in files_to_restore.items():
    print(f"File: {fname}")
    for op in ops:
        print(f"  Step {op['step']}: {op['name']}")
