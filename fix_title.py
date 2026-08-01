"""Fix: move title generation outside the DB connection block."""
path = 'backend/main.py'
content = open(path, 'r', encoding='utf-8').read()

lines = content.split('\n')
# Find the line with the smart title comment
target_idx = None
for i, l in enumerate(lines):
    if 'Smart title on first message' in l and 'always generate' in l:
        target_idx = i
        break

if target_idx is None:
    print("Could not find target line")
    for i, l in enumerate(lines[515:530], start=516):
        print(f"{i}: {repr(l)}")
else:
    print(f"Found target at line {target_idx+1}: {repr(lines[target_idx])}")
    # Lines to remove: from target_idx-1 (blank or comment) through the end of the if block
    # We need to:
    # 1. Remove the smart title block from inside conn (lines target_idx to target_idx+6)
    # 2. Add it after the conn block closes
    
    # Find the closing of the conn block (line with just 8 spaces "        ")
    conn_close_idx = None
    for i in range(target_idx, len(lines)):
        if lines[i].strip() == '' and i > target_idx + 3:
            conn_close_idx = i
            break
    
    print(f"Conn close at line {conn_close_idx+1 if conn_close_idx else 'NOT FOUND'}")
    
    # Build the replacement - remove the title block from inside conn
    # and add it after
    new_lines = lines[:target_idx-1]  # remove blank line before comment too
    new_lines.append('            )')  # close the execute() call - line 517
    new_lines.append('')
    # close conn block - nothing needed as the ) is already there
    # Now add the title block AFTER the conn block
    new_lines.append('        # Title generation OUTSIDE conn block')
    new_lines.append('        # LLM call must not hold a DB connection open for 10+ seconds')
    new_lines.append('        if is_first_message:')
    new_lines.append('            smart_title = await _generate_title(provider, body.message)')
    new_lines.append('            async with get_conn() as conn2:')
    new_lines.append('                await conn2.execute(')
    new_lines.append('                    "UPDATE sessions SET title = %s WHERE id = %s",')
    new_lines.append('                    (smart_title, session_id),')
    new_lines.append('                )')
    new_lines.append('            print(f"[title] generated: {smart_title!r}")')
    new_lines.append('')
    # Add rest of file from the Final event line
    for i, l in enumerate(lines):
        if '# Final event' in l:
            new_lines.extend(lines[i:])
            break
    
    result = '\n'.join(new_lines)
    open(path, 'w', encoding='utf-8').write(result)
    print("SUCCESS")
    
    # Verify
    v = open(path, 'r', encoding='utf-8').read()
    if 'OUTSIDE conn block' in v:
        print("Verified: title is now outside conn block")
    else:
        print("VERIFY FAILED")
    
