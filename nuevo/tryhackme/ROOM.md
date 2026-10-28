# Dragon Root — TryHackMe room content

Paste-ready tasks, questions, answers and hints. Flags come straight from
`ansible/group_vars/all.yml` (the single source of truth).

> Notes:
> 1. **Goku's SSH password = `chichi`** (a rockyou entry, set in `all.yml` as
>    both goku's OS password and `ssh_loot_pass`). Verify it's in your copy:
>    `grep -nx chichi /usr/share/wordlists/rockyou.txt`.
> 2. Room text below is in **English** (matching your editor examples). Say the
>    word and I'll give you the Spanish version.

---

## Task 1 — Mission Briefing  (Introduction, no answer)

**Title:** Operation: Gather the Dragon Balls

You are an IT operator at **Capsule Corporation** in **2024**. Digging through
old incident logs, you find a vulnerability that was live back in **2015** — and
a desperate message Bulma once left for Goku over an *ancient* system, because
the main comms were down.

Freezer has returned and is hunting the **7 Dragon Balls**. If he gathers them
all, his wish cannot be stopped. So you slip into the time machine, travel back
to 2015 — where every bug is still exploitable — and race to collect the seven
balls before he does.

> The whole stack is frozen in 2015. You, the attacker from the future, already
> know the CVE... which is exactly why nothing here is patched.

Deploy the machine, give it a minute to boot, and (optionally) map the host:

```
<MACHINE_IP>   capsulecorp.thm
```

**Question:** I have deployed the machine and I'm ready to gather the Dragon Balls.
**Answer:** *(no answer — mark complete)*

---

## Task 2 — Reconnaissance

Every hunt starts with a full scan. The services here are old and mail-driven.

**Q1.** How many TCP ports are open?
**Answer:** `4`
**Hint:** Scan every port, not just the top 1000 — `nmap -p- -sV <IP>`.

**Q2.** Bulma wrote to Goku through an "old system". Which legacy mail service
(and port) is that?
**Answer:** `POP3`
**Hint:** Read the web landing page (port 80) and check port 110 in your scan.

---

## Task 3 — The One-Star Ball  🟠

Bulma's message drops clues about where the balls are hidden. The first one is
*very* close to where you land.

**Q1.** What is the flag of the **1st** Dragon Ball?
**Answer:** `CAPSULE{0n3_st4r_ftp_4n0nym0us}`
**Hint:** FTP (21) allows the `anonymous` login with a blank password. Grab every
file — `employee_roster.txt` names who to target next.

---

## Task 4 — The Two-Star Ball  🟠🟠

The roster says one employee reused a laughably weak password.

**Q1.** What is Bulma's POP3 password?
**Answer:** `dragon`
**Hint:** She's an R&D Director who clearly loves Dragon Balls... the obvious
guess works.

**Q2.** What is the flag of the **2nd** Dragon Ball?
**Answer:** `CAPSULE{tw0_st4rs_p0p3_m41lb0x}`
**Hint:** `nc <IP> 110`, log in as bulma, `RETR` all 3 emails. The keepsake email
carries a base64 attachment — decode it.

---

## Task 5 — The Three-Star Ball  🟠🟠🟠

Bulma emailed Goku his dashboard password, and Vegeta emailed a security advisory.

**Q1.** What password did Bulma email Goku for the Dragon Radar Dashboard?
**Answer:** `9000`
**Hint:** It's in the first email in bulma's mailbox.

**Q2.** Which CVE does the dashboard's session cookie suffer from?
**Answer:** `CVE-2024-42069`
**Hint:** Vegeta's email names it; the full advisory is served at
`/security/CVE-2024-42069`.

**Q3.** What is the flag of the **3rd** Dragon Ball?
**Answer:** `CAPSULE{thr33_st4rs_w3b_d3s3r14l}`
**Hint:** The `radar_session` cookie is an **unsigned Python pickle** — craft a
`__reduce__` payload for RCE and catch a shell as `www-data`.

---

## Task 6 — The Four-Star Ball (stolen by Freezer)  🟠🟠🟠🟠

Freezer's soldiers hit the same RCE first and sealed this ball with a toy
"ransomware". Don't pay — recover it for free.

**Q1.** What is the hidden web path of the free "No More Capsule" recovery portal?
**Answer:** `/recovery`
**Hint:** The ransom note (`LEEME_RESCATE.txt`) sneers that it exists but won't
name it — fuzz the web root (`gobuster`, medium wordlist).

**Q2.** What is the flag of the **4th** Dragon Ball?
**Answer:** `CAPSULE{f0ur_st4rs_fr33d_fr0m_fr13z4}`
**Hint:** The file extension is the ransomware family. Feed it to `/recovery` to
get the leaked key, then `openssl enc -d -aes-256-cbc -pbkdf2 -k '<key>'`.

---

## Task 7 — "Goku is too brute"  (SSH brute force + user flag)  🥋

Bulma left Goku plenty of clues... but Goku is way too **brute** to figure
anything out on his own. He just reused some dumb password everywhere.

**Q1.** What is Goku's SSH password?
**Answer:** `chichi`
**Hint:** Goku is *brute* — so brute-force him. `hydra -l goku -P <wordlist>
ssh://<IP>`. (A sharp attacker could also loot it from `config.py` after the RCE.)

**Q2.** What is the **user** flag?
**Answer:** `THM{us3r_g0ku_p0w3r_l3v3l_9000}`
**Hint:** It's in goku's home directory once you're in.

---

## Task 8 — The Five-Star Ball (Gravity Chamber)  🟠🟠🟠🟠🟠

Goku hid this one inside his training gear — a console that only answers locally.

**Q1.** What port is the internal Gravity Chamber listening on?
**Answer:** `8081`
**Hint:** It never showed up in your external nmap. As goku, run `ss -tlnp` — it's
bound to `127.0.0.1`. Read `training/memories/NOTA_camara.txt`.

**Q2.** What is the flag of the **5th** Dragon Ball?
**Answer:** `CAPSULE{f1v3_st4rs_g0ku_h0m3}`
**Hint:** Forward the port to your box (`ssh -L 8081:127.0.0.1:8081 goku@<IP>`),
open `http://localhost:8081`, and train at **100x** gravity.

---

## Task 9 — The Six-Star Ball (become root)  🟠🟠🟠🟠🟠🟠

**Q1.** Which binary is abused in the `sudo` wildcard injection?
**Answer:** `tar`
**Hint:** `sudo -l` shows `radar-backup.sh *`. It runs an unquoted `tar ... *` —
the classic GTFOBins `--checkpoint-action` wildcard trick.

**Q2.** What is the flag of the **6th** Dragon Ball?
**Answer:** `CAPSULE{s1x_st4rs_sud0_w1ldc4rd}`
**Hint:** After rooting, it's in `/root/.secrets/`.

**Q3.** What is the **root** flag?
**Answer:** `THM{r00t_sh3nl0ng_gr4nts_y0ur_w1sh}`
**Hint:** `/root/root.txt`.

---

## Task 10 — The Seven-Star Ball (Shenlong's Altar)  🟠🟠🟠🟠🟠🟠🟠

The last ball isn't a file — it's sealed in the Altar web app, and Shenlong only
wakes for a flawless ritual.

**Q1.** What power level must you *exceed* to wake Shenlong?
**Answer:** `9000`
**Hint:** Watch the scouter... "It's OVER 9000!"

**Q2.** What is the flag of the **7th** Dragon Ball?
**Answer:** `CAPSULE{s3v3n_st4rs_w1sh_gr4nt3d}`
**Hint:** Kami-sama is dead, so **Dende** guards the 7th ball at the altar. As
root, loot the **Seal of Ki** from `/opt/shenlong/altar/ki_sigil`. Open `/altar`
through **Burp**, press **"Reclamar la Esfera de 7 Estrellas"**, send the
`POST /altar/summon` to **Repeater** and fix the offering: `planet=earth`,
`kami_sama=alive`, `ki` above 9000, and paste the sigil.

---

## Task 11 — Summon Shenlong (Bonus)  🐉

**Q1.** Gather all seven balls and make your wish. What is the bonus flag?
**Answer:** `THM{t1m3_p4r4d0x_4ll_b4lls}`
**Hint:** As root, copy all 7 balls into `/var/capsule/dragonballs/`, then press
**"Invocar a Shenlong"** on `/altar` (no Burp this time — it only checks you have
7/7). Equivalently: `bash /root/invoke_shenlong.sh`.

---

## Task 12 — Debrief  (Introduction, no answer)

You gathered the seven Dragon Balls before Freezer. The Earth is safe... for now.
A few defensive lessons: never `pickle.loads` untrusted input, don't reuse weak
passwords, don't leave secrets in readable config, quote your `sudo` globs, and
remember that "internal only" is one `ssh -L` away from exposed.

**Answer:** *(no answer — mark complete)*

---

## Brute-force setup (decided)

- **Password: `chichi`** — Goku's wife's name: a perfectly dumb "reused"
  password that nails the "Goku is too brute" joke. Confirmed in `rockyou.txt`
  at **line 865** (shallow → Hydra cracks it over SSH in ~1 minute). Set in
  `all.yml` as **both** goku's OS password (`system_users`) **and**
  `ssh_loot_pass`, so SSH auth, the Hydra brute force, and the `config.py` loot
  all agree.
- **Both paths are valid:** `hydra -l goku -P rockyou.txt ssh://<IP>` (the "brute"
  path for Task 7), or loot it from `config.py` after the web RCE (the shortcut).
- **Before shipping, confirm it's in your wordlist** and check how deep it is
  (SSH brute force is slow, so a password near the top of rockyou is important):
  ```bash
  grep -nx chichi /usr/share/wordlists/rockyou.txt
  ```
  If it is missing or very deep, swap to another Goku-themed rockyou entry
  (e.g. `goku`, `dragonball`, `vegeta`, `gohan`, `kakarot`) — tell me and I'll
  re-wire it.
