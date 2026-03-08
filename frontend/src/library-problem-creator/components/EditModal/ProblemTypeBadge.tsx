import React from 'react';
import { Badge } from '@openedx/paragon';
import { getProblemTypeLabel } from '../../utils/problemTypes';

interface ProblemTypeBadgeProps {
  problemType: string;
  className?: string;
}

const ProblemTypeBadge = ({ problemType, className }: ProblemTypeBadgeProps) => (
  <Badge pill variant="info" className={`small ${className ?? ''}`}>
    {getProblemTypeLabel(problemType)}
  </Badge>
);

export default ProblemTypeBadge;
