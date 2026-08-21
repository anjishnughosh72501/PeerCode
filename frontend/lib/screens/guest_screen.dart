import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../providers/editor_provider.dart';
import '../providers/session_provider.dart';
import '../widgets/editor_widget.dart';
import '../widgets/peer_chip.dart';
import '../widgets/status_bar.dart';

class GuestScreen extends ConsumerWidget {
  const GuestScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final session = ref.watch(sessionNotifierProvider);
    final editor = ref.watch(editorNotifierProvider);
    if (session == null) return const SizedBox.shrink();
    return Scaffold(
      body: Column(
        children: <Widget>[
          Container(
            height: 56,
            padding: const EdgeInsets.symmetric(horizontal: 14),
            decoration: const BoxDecoration(color: Color(0xFF141417), border: Border(bottom: BorderSide(color: Color(0xFF2A2A31)))),
            child: Row(
              children: <Widget>[
                const Text('CodeShare', style: TextStyle(fontWeight: FontWeight.w900)),
                const SizedBox(width: 14),
                Container(width: 8, height: 8, decoration: const BoxDecoration(color: Color(0xFF36D399), shape: BoxShape.circle)),
                const SizedBox(width: 8),
                Expanded(child: Text(editor.hasUnsavedChanges ? 'Waiting for host to save...' : session.filename, overflow: TextOverflow.ellipsis)),
                Wrap(spacing: 8, children: session.peers.map((p) => PeerChip(peer: p)).toList()),
                const SizedBox(width: 10),
                IconButton(
                  onPressed: () async {
                    await ref.read(sessionNotifierProvider.notifier).disconnect();
                    if (context.mounted) context.go('/');
                  },
                  tooltip: 'Disconnect',
                  icon: const Icon(Icons.logout),
                ),
              ],
            ),
          ),
          const Expanded(child: EditorWidget()),
          StatusBar(line: editor.line, col: editor.col, hasUnsavedChanges: editor.hasUnsavedChanges, lastSaved: editor.lastSaved, peerCount: session.peers.length),
        ],
      ),
    );
  }
}
