import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);

export class Rpc3Client {
  constructor(
    private readonly scriptPath: string,
    private readonly username: string,
  ) {}

  async setOutlet(id: number, command: 'on' | 'off' | 'reboot'): Promise<void> {
    const script = `${this.scriptPath}/control.py`;
    await execFileAsync(script, [String(id), this.username, command]);
  }

  async getOutlet(id: number): Promise<boolean> {
    const script = `${this.scriptPath}/state.py`;
    const { stdout } = await execFileAsync(script, [String(id), this.username]);
    return stdout.toString().trim().toLowerCase() === 'true';
  }
}
