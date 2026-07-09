declare module "http" {
  interface IncomingMessage {
    url?: string;
  }
}