import { Virtuoso } from 'react-virtuoso';
import ImageCard from './ImageCard';

function ImageGrid({ images }) {
  const itemsPerRow = 4;
  const rows = [];
  
  for (let i = 0; i < images.length; i += itemsPerRow) {
    rows.push(images.slice(i, i + itemsPerRow));
  }

  return (
    <div className="image-grid-container">
      <Virtuoso
        totalCount={rows.length}
        itemContent={(index) => (
          <div className="grid-row">
            {rows[index].map((image) => (
              <ImageCard key={image} filename={image} />
            ))}
          </div>
        )}
      />
    </div>
  );
}

export default ImageGrid;