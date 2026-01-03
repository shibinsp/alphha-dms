import hashlib
from typing import List, Optional


def compute_hash(data: str) -> str:
    """Compute SHA-256 hash of data."""
    return hashlib.sha256(data.encode()).hexdigest()


def build_merkle_tree(hashes: List[str]) -> List[List[str]]:
    """
    Build a Merkle tree from a list of leaf hashes.
    Returns list of levels, from leaves to root.
    """
    if not hashes:
        return [[]]

    # Start with leaves
    tree = [hashes.copy()]

    # Build tree bottom-up
    while len(tree[-1]) > 1:
        current_level = tree[-1]
        next_level = []

        for i in range(0, len(current_level), 2):
            left = current_level[i]
            # If odd number, duplicate the last hash
            right = current_level[i + 1] if i + 1 < len(current_level) else left
            combined = compute_hash(left + right)
            next_level.append(combined)

        tree.append(next_level)

    return tree


def get_merkle_root(hashes: List[str]) -> str:
    """Get Merkle root from list of leaf hashes."""
    if not hashes:
        return "0" * 64

    tree = build_merkle_tree(hashes)
    return tree[-1][0]


def get_merkle_proof(hashes: List[str], index: int) -> List[tuple[str, str]]:
    """
    Get Merkle proof for a specific leaf at index.
    Returns list of (hash, position) tuples where position is 'L' or 'R'.
    """
    if not hashes or index >= len(hashes):
        return []

    tree = build_merkle_tree(hashes)
    proof = []
    current_index = index

    for level in tree[:-1]:  # Skip root level
        if current_index % 2 == 0:
            # Need right sibling
            sibling_index = current_index + 1
            position = 'R'
        else:
            # Need left sibling
            sibling_index = current_index - 1
            position = 'L'

        if sibling_index < len(level):
            proof.append((level[sibling_index], position))

        current_index = current_index // 2

    return proof


def verify_merkle_proof(
    leaf_hash: str,
    proof: List[tuple[str, str]],
    root: str
) -> bool:
    """Verify a Merkle proof."""
    current = leaf_hash

    for sibling_hash, position in proof:
        if position == 'L':
            current = compute_hash(sibling_hash + current)
        else:
            current = compute_hash(current + sibling_hash)

    return current == root


def verify_chain_integrity(events: List[dict]) -> tuple[bool, Optional[dict]]:
    """
    Verify hash chain integrity of audit events.
    Returns (is_valid, first_error_details).
    """
    if not events:
        return True, None

    for i, event in enumerate(events):
        # First event should have all zeros as previous hash
        if i == 0:
            expected_previous = "0" * 64
        else:
            expected_previous = events[i - 1]["event_hash"]

        if event["previous_hash"] != expected_previous:
            return False, {
                "type": "chain_break",
                "sequence": event.get("sequence_number"),
                "expected_previous": expected_previous,
                "actual_previous": event["previous_hash"]
            }

    return True, None
