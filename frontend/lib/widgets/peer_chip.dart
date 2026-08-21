import 'package:flutter/material.dart';

import '../models/peer.dart';

class PeerChip extends StatelessWidget {
  const PeerChip({super.key, required this.peer});
  final Peer peer;

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: '${peer.name} - ${peer.isHost ? 'Host' : 'Guest'}',
      child: Container(
        height: 28,
        padding: const EdgeInsets.symmetric(horizontal: 10),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(6),
          border: Border.all(color: peer.color.withValues(alpha: 0.4)),
          color: peer.color.withValues(alpha: 0.08),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Container(width: 8, height: 8, decoration: BoxDecoration(color: peer.color, shape: BoxShape.circle)),
            const SizedBox(width: 7),
            Text(peer.name, overflow: TextOverflow.ellipsis),
          ],
        ),
      ),
    );
  }
}
