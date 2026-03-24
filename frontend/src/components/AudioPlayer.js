export function AudioPlayer({ audioRef }) {
  return (
    <div className="voice">
      <div className="label">Remote Audio</div>
      <audio ref={audioRef} autoPlay controls />
    </div>
  );
}
