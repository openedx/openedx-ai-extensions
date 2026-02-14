/**
 * BadgeCarousel Component
 * Displays all generated badges in an interactive carousel
 */

import React, { useState, useCallback } from 'react';
import {
  Card,
  Button,
} from '@openedx/paragon';
import { ChevronLeft, ChevronRight } from '@openedx/paragon/icons';
import { GeneratedBadge } from '../types';

interface BadgeCarouselProps {
  badges: GeneratedBadge[];
  currentBadgeId?: string;
}

const BadgeCarousel: React.FC<BadgeCarouselProps> = ({
  badges,
  currentBadgeId,
}) => {
  const [currentIndex, setCurrentIndex] = useState(badges.length - 1);

  const handlePrev = useCallback(() => {
    setCurrentIndex((prev) => (prev === 0 ? badges.length - 1 : prev - 1));
  }, [badges.length]);

  const handleNext = useCallback(() => {
    setCurrentIndex((prev) => (prev === badges.length - 1 ? 0 : prev + 1));
  }, [badges.length]);

  if (badges.length === 0) {
    return (
      <div className="text-center py-5 text-muted">
        <p style={{ fontSize: '3rem' }}>🎖️</p>
        <p>No badges generated yet</p>
        <p className="small">Create your first badge using the form on the left</p>
      </div>
    );
  }

  const currentBadge = badges[currentIndex];

  return (
    <div className="badge-carousel">
      <Card className="shadow-sm">
        <Card.Header
          title={`Badge ${currentIndex + 1} of ${badges.length}`}
          subtitle={currentBadge.title}
        />
        <Card.Body className="badge-carousel__body">
          <div
            className="badge-carousel__svg-container"
            // todo replace
            dangerouslySetInnerHTML={{ __html: currentBadge.image }}
            aria-label={`Badge: ${currentBadge.title}`}
          />
          <p className="mt-3 mb-0 text-center text-muted">
            {currentBadge.description}
          </p>
        </Card.Body>
      </Card>

      {/* Navigation Controls */}
      {badges.length > 1 && (
        <div className="badge-carousel__controls mt-3 d-flex gap-2 justify-content-center">
          <Button
            variant="outline-secondary"
            size="sm"
            onClick={handlePrev}
            icon={ChevronLeft}
            iconPosition="left"
          >
            Previous
          </Button>

          {/* Dot Indicators */}
          <div className="badge-carousel__dots d-flex gap-2 align-items-center">
            {badges.map((badge, index) => (
              <button
                key={badge.id}
                className={`badge-carousel__dot ${index === currentIndex ? 'active' : ''}`}
                onClick={() => setCurrentIndex(index)}
                aria-label={`Go to badge ${index + 1}`}
                type="button"
              />
            ))}
          </div>

          <Button
            variant="outline-secondary"
            size="sm"
            onClick={handleNext}
            icon={ChevronRight}
            iconPosition="right"
          >
            Next
          </Button>
        </div>
      )}
    </div>
  );
};

export default BadgeCarousel;
