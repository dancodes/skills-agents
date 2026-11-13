---
name: gitlab-screenshots
description: Upload local screenshots to GitLab and add them to a merge request's description with glab and curl. Use when the user asks to add, attach or embed screenshots or images in a GitLab MR, or invokes /gitlab-screenshots.
---

# gitlab-screenshots

Input: a merge request (URL or `!<iid>`) and one or more local image files.
From an MR URL `https://gitlab.com/<group>/<project>/-/merge_requests/<iid>`,
take `<group>/<project>` as the project path and `<iid>` as the MR number.

## Steps

1. **Look at every image.** Open each file with the Read tool before you
   upload it. Uploading publishes it to GitLab, so confirm it shows what the
   MR claims and holds nothing private beyond test data. Done when you have
   seen each file and can name in one line what it shows.

2. **Read the current description.** Keep every line of it, above all
   `Closes <ticket>` lines that link the MR to its ticket:
   ```bash
   P=$(python3 -c 'import sys,urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=""))' "<group>/<project>")
   glab api "projects/$P/merge_requests/<iid>" | python3 -c 'import json,sys; print(json.load(sys.stdin)["description"])'
   ```

3. **Upload each image with curl and a Bearer token.** glab's token is an
   OAuth token: send it as `Authorization: Bearer`. The `PRIVATE-TOKEN`
   header returns `401 Unauthorized`, and `glab api -F file=@...` sends no
   multipart body and returns `HTTP 400`.
   ```bash
   T=$(glab config get token --host gitlab.com)
   curl -s -H "Authorization: Bearer $T" -F "file=@<image.png>" \
     "https://gitlab.com/api/v4/projects/$P/uploads" \
     | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("markdown", d))'
   ```
   Done when each upload printed a `![name](/uploads/<hash>/<file>)` line.
   Any other output is the error; stop and report it verbatim.

4. **Write the new description to a file.** Put the existing description
   first, unchanged, then a `## Screenshots` section. Give each image one
   plain sentence that says what it shows and the figures to check, then its
   markdown line from step 3. The `/uploads/...` paths are relative to the
   project and render only in that project.

5. **Update the MR:**
   ```bash
   glab mr update <iid> -R "<group>/<project>" --description "$(cat <desc-file>)"
   ```
   Done when glab prints `✓ updated description`. Report the MR URL and one
   line per image.
