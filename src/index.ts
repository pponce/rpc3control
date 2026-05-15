import type { API } from 'homebridge';
import { Rpc3Platform } from './platform';

export = (api: API): void => {
  api.registerPlatform('homebridge-rpc3control', 'RPC3Control', Rpc3Platform);
};
