#!/usr/bin/env python3
"""Sauvegarde locale privée des bases du cours, sans mot de passe dans les arguments."""

import datetime
import os
from pathlib import Path
import re
import subprocess


def backup():
    if os.geteuid() != 0:
        raise RuntimeError("Administration root requise.")
    os.umask(0o077)
    destination = Path("/var/backups/ihme")
    destination.mkdir(mode=0o700, parents=True, exist_ok=True)
    query = "SELECT datname FROM pg_database WHERE datname='ihme_suivi' OR datname ~ '^ihme_p[0-9]{2}$' ORDER BY datname"
    databases = subprocess.check_output(
        [
            "docker",
            "exec",
            "ihme-platform-db-1",
            "psql",
            "-U",
            "platform_admin",
            "-d",
            "postgres",
            "-Atc",
            query,
        ],
        text=True,
    ).splitlines()
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for database in databases:
        if not re.fullmatch(r"ihme_(suivi|p[0-9]{2})", database):
            raise ValueError("Nom de base invalide.")
        target = destination / (database + "-" + stamp + ".dump")
        temporary = target.with_suffix(".tmp")
        command = [
            "docker",
            "exec",
            "ihme-platform-db-1",
            "pg_dump",
            "-U",
            "platform_admin",
            "-d",
            database,
            "-Fc",
            "--no-owner",
            "--no-acl",
        ]
        if database == "ihme_suivi":
            command.append("--exclude-table-data=public.sessions")
        with temporary.open("wb") as output:
            subprocess.run(
                command, stdout=output, stderr=subprocess.PIPE, check=True, timeout=180
            )
        temporary.replace(target)
        for old in sorted(destination.glob(database + "-*.dump"), reverse=True)[7:]:
            old.unlink()
    print(
        str(len(databases))
        + " bases sauvegardées localement ; 7 versions conservées par base."
    )


if __name__ == "__main__":
    backup()
