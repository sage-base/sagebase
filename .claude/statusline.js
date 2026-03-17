#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const readline = require('readline');
const { execSync } = require('child_process');

// Constants
const COMPACTION_THRESHOLD = 200000 * 0.8

// Read JSON from stdin
let input = '';
process.stdin.on('data', chunk => input += chunk);
process.stdin.on('end', async () => {
  try {
    const data = JSON.parse(input);

    // Extract values
    const model = data.model?.display_name || 'Unknown';
    const workingDir = data.workspace?.current_dir || data.cwd || '.';
    const currentDir = path.basename(workingDir);
    const sessionId = data.session_id;

    // Calculate token usage for current session
    let totalTokens = 0;

    if (sessionId) {
      // Find all transcript files
      const projectsDir = path.join(process.env.HOME, '.claude', 'projects');

      if (fs.existsSync(projectsDir)) {
        // Get all project directories
        const projectDirs = fs.readdirSync(projectsDir)
          .map(dir => path.join(projectsDir, dir))
          .filter(dir => fs.statSync(dir).isDirectory());

        // Search for the current session's transcript file
        for (const projectDir of projectDirs) {
          const transcriptFile = path.join(projectDir, `${sessionId}.jsonl`);

          if (fs.existsSync(transcriptFile)) {
            totalTokens = await calculateTokensFromTranscript(transcriptFile);
            break;
          }
        }
      }
    }

    // Calculate percentage
    const percentage = Math.min(100, Math.round((totalTokens / COMPACTION_THRESHOLD) * 100));

    // Format token display
    const tokenDisplay = formatTokenCount(totalTokens);

    // Color coding for percentage
    let percentageColor = '\x1b[32m'; // Green
    if (percentage >= 70) percentageColor = '\x1b[33m'; // Yellow
    if (percentage >= 90) percentageColor = '\x1b[31m'; // Red

    // Get git branch
    let gitBranch = '';
    try {
      gitBranch = execSync('git rev-parse --abbrev-ref HEAD', {
        cwd: workingDir,
        encoding: 'utf8',
        stdio: ['pipe', 'pipe', 'ignore']
      }).trim();
    } catch (error) {
      // Not in a git repo
    }

    // Get port info from docker-compose.override.yml
    const portInfo = getWorktreePortInfo(workingDir);

    // Build status line with newlines
    const lines = [];
    lines.push(`[${model}] 📁 ${currentDir}`);
    if (gitBranch) lines.push(`🌿 ${gitBranch}`);
    if (portInfo) lines.push(`🔌 ${portInfo}`);
    lines.push(`🪙 ${tokenDisplay} | ${percentageColor}${percentage}%\x1b[0m`);

    console.log(lines.join('\n'));
  } catch (error) {
    // Fallback status line on error
    console.log('[Error] 📁 . | 🪙 0 | 0%');
  }
});

async function calculateTokensFromTranscript(filePath) {
  return new Promise((resolve, reject) => {
    let lastUsage = null;

    const fileStream = fs.createReadStream(filePath);
    const rl = readline.createInterface({
      input: fileStream,
      crlfDelay: Infinity
    });

    rl.on('line', (line) => {
      try {
        const entry = JSON.parse(line);

        // Check if this is an assistant message with usage data
        if (entry.type === 'assistant' && entry.message?.usage) {
          lastUsage = entry.message.usage;
        }
      } catch (e) {
        // Skip invalid JSON lines
      }
    });

    rl.on('close', () => {
      if (lastUsage) {
        // The last usage entry contains cumulative tokens
        const totalTokens = (lastUsage.input_tokens || 0) +
          (lastUsage.output_tokens || 0) +
          (lastUsage.cache_creation_input_tokens || 0) +
          (lastUsage.cache_read_input_tokens || 0);
        resolve(totalTokens);
      } else {
        resolve(0);
      }
    });

    rl.on('error', (err) => {
      reject(err);
    });
  });
}

function formatTokenCount(tokens) {
  if (tokens >= 1000000) {
    return `${(tokens / 1000000).toFixed(1)}M`;
  } else if (tokens >= 1000) {
    return `${(tokens / 1000).toFixed(1)}K`;
  }
  return tokens.toString();
}

function getWorktreePortInfo(workingDir) {
  try {
    const overridePath = path.join(workingDir, 'docker', 'docker-compose.override.yml');
    if (!fs.existsSync(overridePath)) {
      return '';
    }

    const content = fs.readFileSync(overridePath, 'utf8');

    // ホスト側ポートを抽出（"hostPort:containerPort" の hostPort部分）
    const portMap = {};
    const lines = content.split('\n');
    let currentService = null;

    for (const line of lines) {
      const serviceMatch = line.match(/^\s{2}(\S+):/);
      if (serviceMatch && serviceMatch[1] !== 'ports') {
        currentService = serviceMatch[1];
      }
      const portMatch = line.match(/- "(\d+):(\d+)"/);
      if (portMatch && currentService) {
        const hostPort = portMatch[1];
        const containerPort = portMatch[2];
        // 主要ポートのみラベル付きで表示
        if (containerPort === '8501') {
          portMap['UI'] = hostPort;
        } else if (containerPort === '5432') {
          portMap['DB'] = hostPort;
        } else if (containerPort === '8050') {
          portMap['BI'] = hostPort;
        }
      }
    }

    const parts = Object.entries(portMap).map(([label, port]) => `${label}:${port}`);
    if (parts.length === 0) return '';
    return parts.join(' ');
  } catch (error) {
    return '';
  }
}
