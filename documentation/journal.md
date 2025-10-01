# Data Visualization

The problem with using plain python data viz libraries was that they are designed for pre-made charts. For the case of mediatic data visualization, these are not a great tool due to the limitations of the customized layer design.

I have tried to implement several different layouts, but each time it is quite hard to replace something or make an edit. Just the basic operation of adding an additional player to the duels chart was a hustle that I could not pull off without spending a lot of hours.

This gave me some headaches, and I decided to find a solution that is helpful for both custom designs for aesthetics and also for data visualization.

### My Solution:

I decided to test with .svg files; I think they are a great fit. I can design custom layouts in figma, and then use the elements in the svg to adjust widths, colors, dynamic texts, etc. with python.