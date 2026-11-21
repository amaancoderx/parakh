#!/usr/bin/env bash
# Put Parakh on one small EC2 server in Mumbai, with HTTPS.
#
#   brew install awscli && aws configure      # once: your own access key, region ap-south-1
#   PARAKH_DOMAIN=<optional name> PARAKH_ACCESS_CODE=<optional code> deploy/aws.sh
#
# What it does: makes a key pair and a firewall rule (22, 80, 443), starts an Ubuntu 24.04
# t3.small, copies this folder (code, .env, saved recogniser answers, the bundled calls) and
# runs deploy/setup.sh on it. HTTPS comes from Caddy on a free <ip>.sslip.io name, so no
# domain is needed. Run it again to push new code to the same server.
#
# The access code is asked for before the server will process NEW audio or make API keys.
# The bundled calls can be played by anyone who has the link.
set -euo pipefail
cd "$(dirname "$0")/.."

REGION=${AWS_REGION:-ap-south-1}
NAME=parakh
KEY=~/.ssh/$NAME.pem
PARAKH_ACCESS_CODE=${PARAKH_ACCESS_CODE-}  # optional: when set, new audio needs this code
aws() { command aws --region "$REGION" --output text "$@" | tr -d '\r'; }  # the Windows CLI ends lines with \r

mkdir -p "$(dirname "$KEY")"
if [ ! -f "$KEY" ]; then
  aws ec2 create-key-pair --key-name $NAME --query KeyMaterial > "$KEY"
  chmod 600 "$KEY"
fi

SG=$(aws ec2 describe-security-groups --filters Name=group-name,Values=$NAME --query 'SecurityGroups[0].GroupId' 2>/dev/null || true)
if [ -z "$SG" ] || [ "$SG" = "None" ]; then
  SG=$(aws ec2 create-security-group --group-name $NAME --description "Parakh demo" --query GroupId)
  for port in 22 80 443; do aws ec2 authorize-security-group-ingress --group-id "$SG" --protocol tcp --port $port --cidr 0.0.0.0/0 > /dev/null; done
fi

ID=$(aws ec2 describe-instances --filters Name=tag:Name,Values=$NAME Name=instance-state-name,Values=running,pending --query 'Reservations[0].Instances[0].InstanceId' 2>/dev/null || true)
if [ -z "$ID" ] || [ "$ID" = "None" ]; then
  AMI=$(aws ssm get-parameter --name /aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id --query Parameter.Value)
  ID=$(aws ec2 run-instances --image-id "$AMI" --instance-type t3.small --key-name $NAME --security-group-ids "$SG" \
        --block-device-mappings 'DeviceName=/dev/sda1,Ebs={VolumeSize=16}' \
        --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$NAME}]" --query 'Instances[0].InstanceId')
  aws ec2 wait instance-running --instance-ids "$ID"
fi
IP=$(aws ec2 describe-instances --instance-ids "$ID" --query 'Reservations[0].Instances[0].PublicIpAddress')
HOST=$(echo "$IP" | tr . -).sslip.io
NAMES="${PARAKH_DOMAIN:+$PARAKH_DOMAIN, }parakh-$HOST, $HOST"  # PARAKH_DOMAIN: your own name for the server, if it has one
echo "server $ID at $IP"

SSH="ssh -i $KEY -o StrictHostKeyChecking=accept-new ubuntu@$IP"
until $SSH true 2>/dev/null; do sleep 4; done

# Code, keys, saved recogniser answers and the bundled calls. Not the test sets, uploads or anyone's saved names.
SKIP=(.venv .git __pycache__ .pytest_cache data/external data/uploads data/memory data/calls data/keys.json data/logs data/real
      research_notes reports web/classic.html)
if command -v rsync > /dev/null; then
  rsync -az --delete -e "ssh -i $KEY" "${SKIP[@]/#/--exclude=}" ./ ubuntu@"$IP":parakh/
else  # Windows (Git Bash) has no rsync: stream a tarball over ssh instead
  tar czf - "${SKIP[@]/#/--exclude=}" . | $SSH "mkdir -p parakh && tar xzf - -C parakh"
fi
$SSH "PARAKH_ACCESS_CODE='$PARAKH_ACCESS_CODE' HOST='$NAMES' bash parakh/deploy/setup.sh"
echo
echo "Live at https://${PARAKH_DOMAIN:-$HOST}${PARAKH_ACCESS_CODE:+   (access code for new audio: $PARAKH_ACCESS_CODE)}"
echo "To remove everything: aws ec2 terminate-instances --region $REGION --instance-ids $ID"
