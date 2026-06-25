# Capsule Corporation — CTF Box (Dragon Ball themed)

A self-contained, deliberately-vulnerable HackTheBox-style **Medium** box.
Theme: collect the 7 Dragon Balls by exploiting Capsule Corp's systems. The
core lesson is **insecure deserialization (CVE-2024-42069, CWE-502)** chained
into a **Linux sudo `tar` wildcard** privilege escalation.

> ⚠️ **Lab use only.** Everything here is intentionally insecure. Build it on an
> **isolated VM** (host-only / NAT lab network) and **never expose it to the
> internet**. The exploit code targets this box and nothing else.

---

## What's in the package

```
DragonRoot/
├── README.md                     # this file
├── ansible/                      # reproducible box build (run on a Debian 12 VM)
│   ├── ansible.cfg
│   ├── inventory.ini
│   ├── site.yml
│   ├── group_vars/all.yml        # SINGLE SOURCE OF TRUTH (flags, creds, versions)
│   └── roles/
│       ├── base/                 # hostname, users, 2015 theming, SSH banner
│       ├── ftp/                  # vsftpd anon + roster/diagram/readme/ball1
│       ├── mail/                 # Dovecot POP3 + bulma mailbox (3 emails, ball2)
│       ├── web/                  # Flask vuln app + SQLite + gunicorn + nginx
│       ├── scheduler/            # systemd timer (benign processor)
│       ├── flags/                # balls 3-5, user.txt, goku ssh, collection dir
│       └── privesc/              # sudoers + radar-backup.sh + Shenlong + mtimes
├── advisory/
│   └── CVE-2024-42069.txt        # NVD-style security advisory
├── exploit/
│   ├── README.md                 # how to run both exploits
│   ├── poc.py                    # standalone Python PoC (pickle RCE)
│   └── metasploit/
│       └── capsule_radar_deserialization.rb
└── writeup/
    └── HTB-CapsuleCorp-Writeup.md # full official-style writeup (all 7 balls)
```

---

## Build it

**Target:** a fresh **Debian 12 (bookworm)** VM (slim is fine). **Control node:**
the VM itself, or your workstation with SSH to it.

```bash
# on the VM (simplest):
sudo apt update && sudo apt install -y ansible
cd ansible
sudo ansible-playbook -i inventory.ini site.yml
```

To provision a remote VM instead, edit `inventory.ini` (Option B) and run the
playbook from your workstation. The playbook is idempotent — re-running it
re-applies state.

When it finishes you'll have four services up (21/22/80/110) and the full
exploit chain in place. Validate by running the chain from a clean recon
(`writeup/HTB-CapsuleCorp-Writeup.md`).

### Exporting an OVA

Build on a VM in VirtualBox/VMware, power off, then
`File → Export Appliance` (or `VBoxManage export`). The box has no build-time
randomness in the flags/creds (all pinned in `group_vars/all.yml`), so exports
are reproducible.

---

## Credentials & flags (spoiler)

| Purpose | Value |
|---|---|
| FTP | `anonymous` / (blank) |
| POP3 | `bulma:dragon` |
| Web dashboard | `goku:9000` (leaked via POP3) |
| SSH | `goku:Kakar0t_SSH_2015!` (looted from `config.py`) |
| User flag | `HTB{us3r_g0ku_p0w3r_l3v3l_9000}` |
| Root flag | `HTB{r00t_sh3nl0ng_gr4nts_y0ur_w1sh}` |
| Bonus | `HTB{t1m3_p4r4d0x_4ll_b4lls}` |

All 7 `CAPSULE{...}` dragon-ball flags and their locations are in the writeup.

---

## Build-faithfulness notes

A few deliberate, documented choices so the box boots reliably on Debian 12
while keeping the 2015 story intact:

- **vsftpd 3.0.3** and **Dovecot 2.3.x** are Debian 12 natives and match the
  2015 banners exactly.
- **nginx** advertises `Server: nginx/1.18.0` via the `headers-more` module
  (`server_tokens off` + `more_set_headers`); the real package may be newer.
- **OpenSSH** version is whatever Debian ships; the "OpenSSH 8.x / 2015"
  reference is cosmetic banner text only (spoofing the protocol version would
  require recompiling sshd — intentionally out of scope).
- **Flask**: `requirements.txt` documents the 2015 pin (`Flask==1.1.2`) as set
  dressing/loot; the role installs a runtime that boots cleanly on Python 3.11
  (`flask_runtime` in `group_vars/all.yml`). The deserialization bug lives in
  the app's own `session.py` and is independent of the Flask version. (A sharp
  player noticing the mismatch is just another temporal paradox.)

---

## Three time-travel easter eggs (non-blocking)

1. `README_2024.txt` in FTP — a 2024 mtime among 2015 files.
2. Dashboard footer changelog — a v2.4.2 "fix" dated **after** the server's own
   build date (reveals the vulnerable version).
3. `wish_granted.txt` — the bonus flag, only after summoning Shenlong with all 7
   balls collected into `/var/capsule/dragonballs/`.

---

## Acceptance criteria

- [x] 4 services up with dated banners (21 vsftpd, 22 ssh, 80 nginx, 110 pop3)
- [x] FTP anonymous read-only (all write vectors disabled)
- [x] POP3 `bulma:dragon` returns exactly 3 emails
- [x] Web `goku:9000` login works; `radar_session` is unsigned pickle
- [x] PoC yields a reliable `www-data` reverse shell
- [x] `config.py` readable by www-data; SSH as goku works
- [x] `sudo -l` for goku shows only `radar-backup.sh *`; injection yields root
- [x] All 7 dragon balls at exact paths/permissions; user.txt & root.txt exact
- [x] `invoke_shenlong.sh` grants bonus only with 7/7 balls collected
- [x] No kernel exploit or hash cracking required (Medium)
- [x] 3 non-blocking time-travel easter eggs present
