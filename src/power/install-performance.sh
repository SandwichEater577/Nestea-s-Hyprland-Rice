#!/usr/bin/env bash
set -euo pipefail
source_dir=$(cd -- "$(dirname -- "$0")" && pwd)
backup_dir="/var/backups/nestea-performance-$(date +%Y%m%d-%H%M%S)"
install -d -m 700 "$backup_dir"
for target in /etc/tlp.d/10-laptop.conf /etc/systemd/zram-generator.conf /etc/sysctl.d/90-zram.conf /etc/tmpfiles.d/nestea-zram.conf; do
    if [[ -e "$target" ]]; then cp --parents -a "$target" "$backup_dir/"; fi
done
install -Dm644 "$source_dir/10-laptop.conf" /etc/tlp.d/10-laptop.conf
install -Dm644 "$source_dir/zram-generator.conf" /etc/systemd/zram-generator.conf
install -Dm644 "$source_dir/90-zram.conf" /etc/sysctl.d/90-zram.conf
install -Dm644 "$source_dir/zram-tmpfiles.conf" /etc/tmpfiles.d/nestea-zram.conf
systemd-tmpfiles --create /etc/tmpfiles.d/nestea-zram.conf
systemctl daemon-reload
systemctl start dev-zram0.swap
sysctl -p /etc/sysctl.d/90-zram.conf
tlp start
systemctl restart tlp-pd.service
printf 'Previous configuration saved to %s\n' "$backup_dir"
