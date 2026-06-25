#!/bin/bash
# ===========================================================================
#  invoke_shenlong.sh  --  summon the Eternal Dragon once all 7 balls are home
#  Run as root (reads /root/wish_granted.txt).
# ===========================================================================
set -u
DBDIR="/var/capsule/dragonballs"

declare -A SOURCE=(
  [1]="FTP anonymous          -> /srv/ftp/dragon_ball_1.txt"
  [2]="POP3 bulma mailbox      -> keepsake email attachment"
  [3]="Web deserialization RCE -> /var/capsule/uploads/processed/"
  [4]="Hidden radar cache      -> /var/capsule/tmp/.radarcache/"
  [5]="goku home               -> /home/goku/training/memories/"
  [6]="root .secrets           -> /root/.secrets/"
  [7]="Shenlong altar          -> /opt/shenlong/altar/"
)

missing=()
for n in 1 2 3 4 5 6 7; do
  [[ -s "$DBDIR/dragon_ball_${n}.txt" ]] || missing+=("$n")
done

if (( ${#missing[@]} > 0 )); then
  echo "The seven dragon balls are not yet gathered."
  echo "Copy each ball you find into:  $DBDIR/dragon_ball_N.txt"
  echo
  echo "Still missing:"
  for n in "${missing[@]}"; do
    printf "   [%s] %s\n" "$n" "${SOURCE[$n]}"
  done
  exit 1
fi

cat <<'SHENLONG'
                 .::.
              .:'  .:
           ,MMM8&&&.:'
          MMMMM88&&&&  .:'        ~ S H E N L O N G ~
         MMMMM88&&&&&&:'
         MMMMM88&&&&&&
       .:MMMMM88&&&&&&
     .:'  MMMMM88&&&&
   .:'   .:MMMMM88&&        "YOU WHO HAVE GATHERED THE
  .:'  .:'  MMM8&&'           SEVEN DRAGON BALLS --
 .:'  .:'                     STATE YOUR WISH."
SHENLONG

echo
echo "All 7 dragon balls verified. The sky darkens. Shenlong rises."
echo "-------------------------------------------------------------"
cat /root/wish_granted.txt
