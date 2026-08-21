import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../models/peer.dart';
import '../providers/peers_provider.dart';
import '../providers/session_provider.dart';
import '../widgets/device_card.dart';

class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  final TextEditingController _hostName = TextEditingController(text: 'Host');
  final TextEditingController _guestName = TextEditingController(text: 'Guest');
  final TextEditingController _filePath = TextEditingController();
  DiscoveredHost? _selected;
  bool _busy = false;

  @override
  void dispose() {
    _hostName.dispose();
    _guestName.dispose();
    _filePath.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final discovered = ref.watch(peersNotifierProvider).discovered;
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1120),
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: LayoutBuilder(
                builder: (context, constraints) {
                  final cards = <Widget>[_hostCard(context), _joinCard(context, discovered)];
                  if (constraints.maxWidth < 760) {
                    return ListView(children: <Widget>[cards[0], const SizedBox(height: 16), cards[1]]);
                  }
                  return Row(crossAxisAlignment: CrossAxisAlignment.stretch, children: <Widget>[Expanded(child: cards[0]), const SizedBox(width: 16), Expanded(child: cards[1])]);
                },
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _hostCard(BuildContext context) {
    return _panel(
      title: 'Host a File',
      subtitle: 'Share a file from your machine',
      children: <Widget>[
        TextField(controller: _hostName, decoration: const InputDecoration(labelText: 'Your name')),
        const SizedBox(height: 12),
        Row(
          children: <Widget>[
            Expanded(child: TextField(controller: _filePath, decoration: const InputDecoration(labelText: 'File path'))),
            const SizedBox(width: 8),
            FilledButton.icon(onPressed: _pickFile, icon: const Icon(Icons.folder_open), label: const Text('Browse')),
          ],
        ),
        const Spacer(),
        FilledButton.icon(onPressed: _busy ? null : _startHost, icon: const Icon(Icons.wifi_tethering), label: const Text('Start Hosting')),
      ],
    );
  }

  Widget _joinCard(BuildContext context, List<DiscoveredHost> discovered) {
    return _panel(
      title: 'Join a Session',
      subtitle: 'Connect to someone on your network',
      children: <Widget>[
        TextField(controller: _guestName, decoration: const InputDecoration(labelText: 'Your name')),
        const SizedBox(height: 14),
        Expanded(
          child: discovered.isEmpty
              ? const Center(child: Text('Searching for hosts on your network...', style: TextStyle(color: Color(0xFF9A9AAA))))
              : ListView.separated(
                  itemCount: discovered.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 10),
                  itemBuilder: (_, index) {
                    final host = discovered[index];
                    return DeviceCard(host: host, selected: _selected?.ip == host.ip, onTap: () => setState(() => _selected = host));
                  },
                ),
        ),
        const SizedBox(height: 12),
        FilledButton.icon(onPressed: _busy || _selected == null ? null : _join, icon: const Icon(Icons.login), label: const Text('Connect')),
      ],
    );
  }

  Widget _panel({required String title, required String subtitle, required List<Widget> children}) {
    return Container(
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(color: const Color(0xFF1C1C21), borderRadius: BorderRadius.circular(12), border: Border.all(color: const Color(0xFF2A2A31))),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
        Text(title, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w800)),
        const SizedBox(height: 6),
        Text(subtitle, style: const TextStyle(color: Color(0xFF9A9AAA))),
        const SizedBox(height: 22),
        ...children,
      ]),
    );
  }

  Future<void> _pickFile() async {
    final result = await FilePicker.platform.pickFiles();
    final path = result?.files.single.path;
    if (path != null) _filePath.text = path;
  }

  Future<void> _startHost() async {
    if (_filePath.text.trim().isEmpty) return;
    await _guard(() async {
      await ref.read(sessionNotifierProvider.notifier).startHost(_hostName.text.trim(), _filePath.text.trim());
      if (mounted) context.go('/host');
    });
  }

  Future<void> _join() async {
    final selected = _selected;
    if (selected == null) return;
    await _guard(() async {
      await ref.read(sessionNotifierProvider.notifier).joinGuest(_guestName.text.trim(), selected.ip, selected.port);
      if (mounted) context.go('/guest');
    });
  }

  Future<void> _guard(Future<void> Function() action) async {
    setState(() => _busy = true);
    try {
      await action();
    } catch (error) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$error'), backgroundColor: Colors.red));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }
}
