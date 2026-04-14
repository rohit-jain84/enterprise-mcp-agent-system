import { useEffect, useRef, useCallback, useState } from 'react';

export function useAutoScroll(dependencies: unknown[]) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isUserScrolled, setIsUserScrolled] = useState(false);

  const scrollToBottom = useCallback(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, []);

  const handleScroll = useCallback(() => {
    if (!containerRef.current) return;

    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    const distanceFromBottom = scrollHeight - scrollTop - clientHeight;
    setIsUserScrolled(distanceFromBottom > 100);
  }, []);

  useEffect(() => {
    if (!isUserScrolled) {
      scrollToBottom();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...dependencies, isUserScrolled, scrollToBottom]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    container.addEventListener('scroll', handleScroll, { passive: true });
    return () => container.removeEventListener('scroll', handleScroll);
  }, [handleScroll]);

  return { containerRef, scrollToBottom, isUserScrolled };
}
