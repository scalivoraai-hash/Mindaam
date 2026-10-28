/** Keep slow GPUs from accumulating stale city frames across venue transitions. */
export class RenderQueue {
 private pending:WebGLSync|null=null;
 ready(gl:WebGL2RenderingContext|WebGLRenderingContext){
  if(!this.pending||!('clientWaitSync' in gl))return true;
  // Zero timeout polls completion; it never blocks the browser's UI thread.
  if(gl.clientWaitSync(this.pending,0,0)===gl.TIMEOUT_EXPIRED)return false;
  this.dispose(gl);
  return true;
 }
 submitted(gl:WebGL2RenderingContext|WebGLRenderingContext){
  if(!('fenceSync' in gl))return;
  this.pending=gl.fenceSync(gl.SYNC_GPU_COMMANDS_COMPLETE,0);
  gl.flush();
 }
 dispose(gl:WebGL2RenderingContext|WebGLRenderingContext){
  if(this.pending&&'deleteSync' in gl)gl.deleteSync(this.pending);
  this.pending=null;
 }
}
