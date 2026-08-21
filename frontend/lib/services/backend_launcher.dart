import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';

class BackendNotFoundException implements Exception {
  BackendNotFoundException(this.message);
  final String message;

  @override
  String toString() => message;
}

class BackendTimeoutException implements Exception {
  BackendTimeoutException(this.message);
  final String message;

  @override
  String toString() => message;
}

class BackendLauncher {
  static Process? _process;
  static String? _pythonExe;
  static List<String> _pythonArgsPrefix = <String>[];

  static Future<void> launch() async {
    _pythonExe = await _resolvePython();
    final scriptPath = _resolveBackendScript();
    if (await _isAlreadyRunning()) return;

    final process = await Process.start(
      _pythonExe!,
      <String>[..._pythonArgsPrefix, '-u', scriptPath],
      environment: <String, String>{
        ...Platform.environment,
        'PYTHONUNBUFFERED': '1',
      },
      mode: Platform.isWindows
          ? ProcessStartMode.normal
          : ProcessStartMode.normal,
    );
    _process = process;

    final readyCompleter = Completer<void>();

    process.stdout
        .transform(utf8.decoder)
        .transform(const LineSplitter())
        .listen((String line) {
      try {
        final decoded = jsonDecode(line);
        if (decoded is Map<String, Object?> &&
            decoded['status'] == 'ready' &&
            decoded['app'] == 'peercode') {
          if (!readyCompleter.isCompleted) readyCompleter.complete();
          return;
        }
        if (decoded is Map<String, Object?> && decoded['status'] == 'error') {
          if (!readyCompleter.isCompleted) {
            readyCompleter
                .completeError('PeerCode backend error: ${decoded["message"]}');
          }
          return;
        }
        debugPrint('[PeerCode backend] $line');
      } catch (_) {
        debugPrint('[PeerCode backend] $line');
      }
    });

    process.stderr.transform(utf8.decoder).listen((String line) {
      debugPrint('[PeerCode stderr] $line');
    });

    process.exitCode.then((int code) {
      if (!readyCompleter.isCompleted) {
        readyCompleter.completeError(
            'PeerCode backend exited before startup completed. Exit code: $code');
      }
    });

    try {
      await readyCompleter.future.timeout(const Duration(seconds: 15));
    } on TimeoutException {
      process.kill();
      throw BackendTimeoutException(
          'PeerCode backend did not start within 15 seconds.');
    }
  }

  static Future<void> dispose() async {
    _process?.kill();
    _process = null;
  }

  static Future<String> _resolvePython() async {
    final envPython = Platform.environment['PEERCODE_PYTHON'];
    if (envPython != null &&
        envPython.trim().isNotEmpty &&
        File(envPython).existsSync()) {
      _pythonArgsPrefix = <String>[];
      return envPython;
    }

    if (Platform.isWindows) {
      for (final candidate in <String>['python', 'python3', 'py']) {
        final result = await Process.run('where.exe', <String>[candidate]);
        if (result.exitCode == 0) {
          final lines = (result.stdout as String)
              .split(RegExp(r'\r?\n'))
              .where((line) => line.trim().isNotEmpty);
          if (lines.isNotEmpty) {
            _pythonArgsPrefix = candidate == 'py' ? <String>['-3'] : <String>[];
            return lines.first.trim();
          }
        }
      }
    } else {
      for (final candidate in <String>['python3', 'python']) {
        final result = await Process.run('which', <String>[candidate]);
        if (result.exitCode == 0) {
          final path = (result.stdout as String).trim().split('\n').first;
          if (path.isNotEmpty) {
            _pythonArgsPrefix = <String>[];
            return path;
          }
        }
      }
    }

    throw BackendNotFoundException(
      'Could not find Python. Set PEERCODE_PYTHON env var to the full path of your Python executable.',
    );
  }

  static String _resolveBackendScript() {
    final exeDir = File(Platform.resolvedExecutable).parent.path;
    final candidates = <String>[
      '$exeDir/backend/main.py',
      '$exeDir/../backend/main.py',
      '${Directory.current.path}/../backend/main.py',
      '${Directory.current.path}/backend/main.py',
    ];
    for (final candidate in candidates) {
      if (File(candidate).existsSync()) return File(candidate).absolute.path;
    }
    throw BackendNotFoundException(
      'Could not find PeerCode backend script. Tried:\n${candidates.join('\n')}',
    );
  }

  static Future<bool> _isAlreadyRunning() async {
    final client = HttpClient()
      ..connectionTimeout = const Duration(milliseconds: 300);
    try {
      final request = await client
          .getUrl(Uri.parse('http://127.0.0.1:7432/health'))
          .timeout(const Duration(milliseconds: 300));
      final response =
          await request.close().timeout(const Duration(milliseconds: 300));
      final body = await response
          .transform(utf8.decoder)
          .join()
          .timeout(const Duration(milliseconds: 300));
      return response.statusCode == 200 && body.contains('"app": "peercode"');
    } catch (_) {
      return false;
    } finally {
      client.close(force: true);
    }
  }
}
