"""Inspecte un objet MinIO sans le télécharger en entier.

Utilise un flux S3 (get_object) et ne lit que les premières lignes (ou les
premiers octets si le fichier n'est pas du texte ligne-par-ligne), utile pour
vérifier le contenu de fichiers volumineux dans bronze/silver/gold sans
attendre un téléchargement complet.

Les 5 fichiers JSON du Yelp Open Dataset (bronze/yelp/json/) :
    yelp_academic_dataset_business.json  - fiche de chaque commerce (adresse,
                                            catégories, note moyenne, horaires...)
    yelp_academic_dataset_review.json    - avis complets (texte, note, votes
                                            useful/funny/cool) - le plus gros fichier (~5 Go)
    yelp_academic_dataset_user.json      - profils utilisateurs (ancienneté,
                                            amis, statut elite, compteurs)
    yelp_academic_dataset_tip.json       - mini-avis courts ("tips"), sans note
    yelp_academic_dataset_checkin.json   - dates de visite par commerce
                                            (un enregistrement par business_id)

Usage:
    python utils/peek_bronze.py --key yelp/json/yelp_academic_dataset_business.json
    python utils/peek_bronze.py --key yelp/photos.zip --bucket bronze
    python utils/peek_bronze.py --key yelp/json/yelp_academic_dataset_review.json --lines 5

    # 10 lignes ALÉATOIRES (échantillonnage par réservoir, un seul passage
    # streaming sur le fichier - toujours sans téléchargement sur disque) :
    python utils/peek_bronze.py --key yelp/json/yelp_academic_dataset_business.json --random 10
    python utils/peek_bronze.py --key yelp/json/yelp_academic_dataset_review.json --random 10
    python utils/peek_bronze.py --key yelp/json/yelp_academic_dataset_user.json --random 10
    python utils/peek_bronze.py --key yelp/json/yelp_academic_dataset_tip.json --random 10
    python utils/peek_bronze.py --key yelp/json/yelp_academic_dataset_checkin.json --random 10
"""
import argparse
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "conf"))
from s3_client import get_client  # noqa: E402


def peek_random(bucket: str, key: str, n: int) -> None:
    """Échantillonnage par réservoir : n lignes uniformément aléatoires parmi
    tout le fichier, en un seul passage streaming (pas besoin de connaître le
    nombre total de lignes à l'avance, pas de téléchargement sur disque)."""
    client = get_client()
    obj = client.get_object(Bucket=bucket, Key=key)
    reservoir: list[bytes] = []
    for i, line in enumerate(obj["Body"].iter_lines()):
        if i < n:
            reservoir.append(line)
        else:
            j = random.randint(0, i)
            if j < n:
                reservoir[j] = line
    for line in reservoir:
        print(line.decode("utf-8", errors="replace")[:500])
        print("---")


def peek(bucket: str, key: str, lines: int, max_bytes: int) -> None:
    client = get_client()
    head = client.head_object(Bucket=bucket, Key=key)
    print(f"s3://{bucket}/{key}  ({head['ContentLength'] / (1024**2):.1f} MB)")
    print("---")

    obj = client.get_object(Bucket=bucket, Key=key)
    body = obj["Body"]

    if key.endswith(".json"):
        for i, line in enumerate(body.iter_lines()):
            if i >= lines:
                break
            print(line.decode("utf-8", errors="replace")[:500])
            print("---")
    else:
        chunk = body.read(max_bytes)
        try:
            print(chunk.decode("utf-8"))
        except UnicodeDecodeError:
            print(f"[binaire] {len(chunk)} premiers octets : {chunk[:80]!r}...")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bucket", default="bronze")
    parser.add_argument("--key", required=True, help="Chemin de l'objet dans le bucket")
    parser.add_argument("--lines", type=int, default=3, help="Nb de lignes (les N premières) pour les fichiers JSON")
    parser.add_argument("--random", type=int, default=0, help="Nb de lignes ALÉATOIRES à afficher (JSON uniquement)")
    parser.add_argument("--max-bytes", type=int, default=2000, help="Octets à lire pour les fichiers non-JSON")
    args = parser.parse_args()

    if args.random:
        print(f"s3://{args.bucket}/{args.key}  (échantillon aléatoire de {args.random} lignes)")
        print("---")
        peek_random(args.bucket, args.key, args.random)
    else:
        peek(args.bucket, args.key, args.lines, args.max_bytes)


if __name__ == "__main__":
    main()
