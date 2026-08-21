import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';

import 'bridge/bridge_ws.dart';
import 'models/peer.dart';
import 'providers/editor_provider.dart';
import 'providers/peers_provider.dart';
import 'providers/session_provider.dart';
import 'screens/error_screen.dart';
import 'screens/guest_screen.dart';
import 'screens/home_screen.dart';
import 'screens/host_screen.dart';
import 'screens/splash_screen.dart';
import 'services/backend_launcher.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const ProviderScope(child: AppBootstrap()));
}

class AppBootstrap extends StatefulWidget {
  const AppBootstrap({super.key});

  @override
  State<AppBootstrap> createState() => _AppBootstrapState();
}

class _AppBootstrapState extends State<AppBootstrap> {
  String _status = 'Starting PeerCode...';
  String? _error;
  bool _ready = false;

  @override
  void initState() {
    super.initState();
    unawaited(_boot());
  }

  @override
  Widget build(BuildContext context) {
    if (_ready) return const PeerCodeApp();
    if (_error != null) return ErrorScreen(message: _error!, onRetry: _retry);
    return SplashScreen(status: _status);
  }

  Future<void> _boot() async {
    try {
      setState(() {
        _status = 'Locating Python...';
        _error = null;
      });
      await BackendLauncher.launch();
      setState(() => _status = 'Connecting to backend...');
      await Future<void>.delayed(const Duration(milliseconds: 400));
      if (mounted) setState(() => _ready = true);
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    }
  }

  void _retry() {
    setState(() {
      _status = 'Starting PeerCode...';
      _error = null;
      _ready = false;
    });
    unawaited(_boot());
  }
}

class PeerCodeApp extends ConsumerStatefulWidget {
  const PeerCodeApp({super.key});

  @override
  ConsumerState<PeerCodeApp> createState() => _PeerCodeAppState();
}

class _PeerCodeAppState extends ConsumerState<PeerCodeApp> {
  final BridgeWS _bridgeWS = BridgeWS();
  final GoRouter _router = GoRouter(
    routes: <RouteBase>[
      GoRoute(path: '/', builder: (_, __) => const HomeScreen()),
      GoRoute(path: '/host', builder: (_, __) => const HostScreen()),
      GoRoute(path: '/guest', builder: (_, __) => const GuestScreen()),
    ],
  );
  StreamSubscription<Map<String, Object?>>? _events;

  @override
  void initState() {
    super.initState();
    unawaited(_bridgeWS.connect());
    _events = _bridgeWS.events.listen(_handleEvent);
  }

  @override
  void dispose() {
    _events?.cancel();
    _bridgeWS.dispose();
    unawaited(BackendLauncher.dispose());
    _router.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = ThemeData.dark(useMaterial3: true).copyWith(
      scaffoldBackgroundColor: const Color(0xFF0D0D0F),
      colorScheme: const ColorScheme.dark(
        primary: Color(0xFF7C84FA),
        surface: Color(0xFF141417),
        error: Colors.redAccent,
      ),
      textTheme: GoogleFonts.interTextTheme(ThemeData.dark().textTheme).apply(
          bodyColor: const Color(0xFFE8E8F0),
          displayColor: const Color(0xFFE8E8F0)),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: const Color(0xFF141417),
        border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(8),
            borderSide: const BorderSide(color: Color(0xFF2A2A31))),
        enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(8),
            borderSide: const BorderSide(color: Color(0xFF2A2A31))),
        focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(8),
            borderSide: const BorderSide(color: Color(0xFF7C84FA))),
      ),
    );
    return MaterialApp.router(
      title: 'PeerCode',
      debugShowCheckedModeBanner: false,
      theme: theme,
      routerConfig: _router,
      builder: (context, child) => child ?? const SizedBox.shrink(),
    );
  }

  void _handleEvent(Map<String, Object?> event) {
    final type = event['type'] as String? ?? '';
    switch (type) {
      case 'text_update':
        ref
            .read(editorNotifierProvider.notifier)
            .applyRemoteText(event['content'] as String? ?? '');
        final filename = event['filename'] as String?;
        if (filename != null) {
          ref.read(sessionNotifierProvider.notifier).setFilename(filename);
        }
        break;
      case 'cursor_update':
        ref.read(editorNotifierProvider.notifier).updateRemoteCursor(
              event['author'] as String? ?? 'Peer',
              event['line'] as int? ?? 1,
              event['col'] as int? ?? 1,
              event['color'] as String? ?? '#7C84FA',
            );
        break;
      case 'peer_list':
        final peers = (event['peers'] as List<Object?>? ?? <Object?>[])
            .whereType<Map<String, Object?>>()
            .map(Peer.fromJson)
            .toList();
        ref.read(peersNotifierProvider.notifier).setConnected(peers);
        ref.read(sessionNotifierProvider.notifier).setPeers(peers);
        break;
      case 'peer_joined':
        final peerMap = event['peer'];
        if (peerMap is Map<String, Object?>) {
          ref
              .read(sessionNotifierProvider.notifier)
              .addPeer(Peer.fromJson(peerMap));
        }
        break;
      case 'peer_left':
        final name = event['name'] as String? ?? '';
        ref.read(sessionNotifierProvider.notifier).removePeer(name);
        ref.read(editorNotifierProvider.notifier).removeRemoteCursor(name);
        break;
      case 'saved':
        final raw = event['timestamp'];
        final seconds = raw is num
            ? raw.toDouble()
            : DateTime.now().millisecondsSinceEpoch / 1000;
        ref.read(editorNotifierProvider.notifier).markSaved(
            DateTime.fromMillisecondsSinceEpoch((seconds * 1000).round()));
        break;
      case 'discovered':
        final hosts = (event['peers'] as List<Object?>? ?? <Object?>[])
            .whereType<Map<String, Object?>>()
            .map(DiscoveredHost.fromJson)
            .toList();
        ref.read(peersNotifierProvider.notifier).setDiscovered(hosts);
        break;
      case 'error':
        _showError(event['message'] as String? ?? 'Unknown bridge error');
        break;
    }
  }

  void _showError(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(message), backgroundColor: Colors.red));
  }
}
