# Demo and proposal

## Proposal

First-time PC builders and students upgrading an existing PC can struggle to match exact CPU, motherboard and RAM models across separate manufacturer pages. PC Parts Check will accept Thai or English parts lists, retrieve specifications and CPU support tables from a small AM4/AM5 catalog, and use a course-proxy agent to call a deterministic compatibility checker. It will cite the evidence for each result and surface missing evidence or BIOS requirements. Evaluation will compare hybrid retrieval with a BM25 baseline on 30 labelled prompts using Recall@3 and MRR@3, and separately score the checker on 19 labelled compatibility cases.

## Screen recording plan (about four minutes)

1. **0:00–0:30.** Open the app and show the Thai question box and direct checker. Explain who uses it and what the catalog covers.
2. **0:30–1:30.** With the course proxy configured, enter `TUF GAMING B550-PLUS + Ryzen 7 5700X3D + KF432C16BBK2/16 ตอนนี้ BIOS 2803 ใช้ได้ไหม`. Show the tool calls and click the CPU Support citation. Explain that the rule checks the BIOS minimum from the board-specific table.
3. **1:30–2:15.** Change BIOS to `2423` and show the conditional verdict. Alternatively run the B650/DDR4 mismatch in the README and show the rule that rejects the combination.
4. **2:15–3:20.** Run `python -m eval.run` with the project interpreter. Show that hybrid Recall@3 was 0.9833 vs 0.9111 for BM25. Open case 27 in `eval/results.json` to show a real retrieval failure. The prompt names one board in full and the second only as WIFI II. Hybrid did not put the second board's support table in the top three.
5. **3:20–4:00.** Show the separate live score from `python -m eval.run --live` after measuring it with your course credentials. Explain one limitation, such as DDR generation checking, and that the checker asks for enough evidence to make a claim.

For the live defence, try a new parts list in the chat form and show the tool calls, sources and `app/checker.py`.
