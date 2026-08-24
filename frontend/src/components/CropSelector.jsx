import React from 'react';
import { Sprout, Leaf, Trees, Flower2, Wheat } from 'lucide-react';

const CROPS = [
  { id: 'paddy', label: 'Paddy (Rice)', icon: Wheat },
  { id: 'cotton', label: 'Cotton', icon: Sprout },
  { id: 'banana', label: 'Banana', icon: Trees },
  { id: 'potato', label: 'Potato', icon: Leaf },
  { id: 'wheat', label: 'Wheat', icon: Flower2 },
];

export default function CropSelector({ activeCrop, onCropSelect }) {
  return (
    <div className="crop-selector-bar">
      <div className="crop-selector-label">
        <Sprout size={14} className="label-icon" />
        <span>CROP PERSONA:</span>
      </div>
      <div className="crop-chips-row">
        {CROPS.map((crop) => {
          const IconComp = crop.icon;
          const isActive = activeCrop === crop.id;
          return (
            <button
              key={crop.id}
              className={`crop-chip ${isActive ? 'active' : ''}`}
              onClick={() => onCropSelect(crop.id)}
            >
              <IconComp size={13} />
              <span>{crop.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
